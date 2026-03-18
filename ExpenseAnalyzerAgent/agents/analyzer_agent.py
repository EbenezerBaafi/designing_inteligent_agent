"""
ANALYZER AGENT  (SPADE)
-----------------------
JID      : analyzer_agent@localhost
Behaviour: CyclicBehaviour — waits for parsed_transactions messages,
           runs full analysis, sends analysis_results to AdvisorAgent.

Prometheus Percepts : parsed_transactions, data_request, category_correction
Prometheus Actions  : categorize_transactions, detect_anomalies,
                      identify_subscriptions, compare_periods, update_history
"""

import json
import math
from collections import defaultdict

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


# ── Beliefs: category keyword rules ──────────────────────────────────────────
CATEGORY_RULES = {
    "Food & Dining":       ["restaurant","cafe","coffee","pizza","burger","food","eat",
                            "kitchen","grill","canteen","lunch","dinner","breakfast",
                            "kfc","shoprite","waakye","chop bar","snack","grocery",
                            "supermarket","market","provisions"],
    "Transport":           ["uber","bolt","trotro","taxi","fuel","petrol","transport",
                            "bus","car","vehicle","parking","toll","ride"],
    "Utilities":           ["ecg","electricity","water","internet","wifi","data","mtn",
                            "vodafone","airtel","telecel","utility","bill","prepaid"],
    "Rent & Housing":      ["rent","landlord","housing","accommodation","apartment",
                            "house","lodge","hostel"],
    "Entertainment":       ["netflix","spotify","youtube","cinema","movie","gaming",
                            "game","subscription","streaming","dstv","showmax"],
    "Health":              ["pharmacy","hospital","clinic","doctor","medical","drug",
                            "health","nhis","dentist","optical"],
    "Education":           ["school","university","college","tuition","course","book",
                            "stationery","fees","exam","study"],
    "Shopping":            ["shop","mall","store","buy","purchase","clothing","shoes",
                            "melcom","palace","fashion"],
    "Savings & Investment":["savings","investment","susu","momo savings",
                            "fixed deposit","pension","insurance"],
}

BUDGET_MAPPING = {
    "Needs":   ["Food & Dining","Transport","Utilities","Rent & Housing","Health","Education"],
    "Wants":   ["Entertainment","Shopping"],
    "Savings": ["Savings & Investment"],
}


# ── Behaviour ─────────────────────────────────────────────────────────────────
class AnalyzeBehaviour(CyclicBehaviour):
    """
    Waits for parsed_transactions or data_request messages.
    Runs analysis pipeline and sends results to AdvisorAgent.
    """

    async def run(self):
        msg = await self.receive(timeout=30)
        if msg is None:
            return

        ontology = msg.get_metadata("ontology")

        # ── PERCEPT: parsed_transactions ──────────────────────────────────
        if ontology == "parsed_transactions":
            parsed = json.loads(msg.body)
            print(f"[AnalyzerAgent] Received {parsed['row_count']} transactions")

            transactions = parsed["transactions"]
            if not transactions:
                print("[AnalyzerAgent] No transactions to analyze.")
                return

            # Run analysis pipeline
            categorized      = self._categorize(transactions)
            totals           = self._compute_totals(categorized)
            anomalies        = self._detect_anomalies(categorized)
            subscriptions    = self._identify_subscriptions(categorized)
            period_comparison= self._compare_periods(totals)
            budget_analysis  = self._apply_budget_rule(totals)

            self._update_history(totals)   # ACTION: update_history

            analysis = {
                "transactions":      categorized,
                "category_totals":   totals,
                "anomalies":         anomalies,
                "subscriptions":     subscriptions,
                "period_comparison": period_comparison,
                "budget_analysis":   budget_analysis,
                "total_spend":       round(sum(t["amount"] for t in categorized), 2),
                "transaction_count": len(categorized),
            }

            # ACTION: send analysis_results → AdvisorAgent
            reply = Message(to=self.agent.advisor_jid)
            reply.set_metadata("performative", "inform")
            reply.set_metadata("ontology", "analysis_results")
            reply.body = json.dumps(analysis)
            await self.send(reply)
            print(f"[AnalyzerAgent] Sent analysis_results to {self.agent.advisor_jid}")

        # ── PERCEPT: data_request ─────────────────────────────────────────
        elif ontology == "data_request":
            req = json.loads(msg.body)
            category = req.get("category")
            history  = self.agent.spending_history
            result   = {
                "category": category,
                "total":    history.get(category, 0),
            }
            reply = Message(to=str(msg.sender))
            reply.set_metadata("performative", "inform")
            reply.set_metadata("ontology", "category_data")
            reply.body = json.dumps(result)
            await self.send(reply)

        # ── PERCEPT: category_correction ─────────────────────────────────
        elif ontology == "category_correction":
            data = json.loads(msg.body)
            desc = data.get("description", "").lower()
            cat  = data.get("category", "")
            self.agent.corrections[desc] = cat
            print(f"[AnalyzerAgent] Correction stored: '{desc}' -> '{cat}'")

    # ── ACTION: categorize_transactions ──────────────────────────────────
    def _categorize(self, transactions):
        result = []
        for t in transactions:
            desc = t["description"].lower()
            if desc in self.agent.corrections:
                cat, conf = self.agent.corrections[desc], "CORRECTED"
            elif t.get("raw_category"):
                raw = t["raw_category"].title()
                if raw in CATEGORY_RULES:
                    cat, conf = raw, "PROVIDED"
                else:
                    cat, conf = self._match_keywords(desc)
            else:
                cat, conf = self._match_keywords(desc)
            result.append({**t, "category": cat, "confidence": conf})
        return result

    def _match_keywords(self, desc):
        for cat, kws in CATEGORY_RULES.items():
            if any(kw in desc for kw in kws):
                return cat, "HIGH"
        return "Other", "LOW"

    # ── ACTION: compute totals ────────────────────────────────────────────
    def _compute_totals(self, transactions):
        totals = defaultdict(float)
        for t in transactions:
            totals[t["category"]] += t["amount"]
        return {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda x: -x[1])}

    # ── ACTION: detect_anomalies ──────────────────────────────────────────
    def _detect_anomalies(self, transactions):
        by_cat = defaultdict(list)
        for t in transactions:
            by_cat[t["category"]].append(t["amount"])
        stats = {}
        for cat, amounts in by_cat.items():
            if len(amounts) >= 2:
                mean = sum(amounts) / len(amounts)
                std  = math.sqrt(sum((x-mean)**2 for x in amounts) / len(amounts))
                stats[cat] = (mean, std)
        anomalies = []
        for t in transactions:
            cat = t["category"]
            if cat in stats and stats[cat][1] > 0:
                z = (t["amount"] - stats[cat][0]) / stats[cat][1]
                if z > 2.0:
                    anomalies.append({**t, "z_score": round(z, 2),
                                      "mean": round(stats[cat][0], 2)})
        return anomalies

    # ── ACTION: identify_subscriptions ───────────────────────────────────
    def _identify_subscriptions(self, transactions):
        groups = defaultdict(list)
        for t in transactions:
            groups[t["description"].lower()].append(t)
        subs = []
        for desc, items in groups.items():
            if len(items) >= 2:
                amounts = [i["amount"] for i in items]
                mean    = sum(amounts) / len(amounts)
                if all(abs(a - mean) / mean < 0.05 for a in amounts):
                    subs.append({
                        "description":  items[0]["description"],
                        "category":     items[0]["category"],
                        "amount":       round(mean, 2),
                        "occurrences":  len(items),
                        "monthly_cost": round(mean, 2),
                        "annual_cost":  round(mean * 12, 2),
                    })
        return subs

    # ── ACTION: compare_periods ───────────────────────────────────────────
    def _compare_periods(self, current_totals):
        history = self.agent.spending_history
        if not history:
            return {"status": "No historical data available."}
        comparison = {}
        for cat, current in current_totals.items():
            if cat in history:
                prev   = history[cat]
                change = current - prev
                pct    = round((change / prev) * 100, 1) if prev else 0
                comparison[cat] = {
                    "current":    current,
                    "previous":   round(prev, 2),
                    "change":     round(change, 2),
                    "pct_change": pct,
                    "trend":      "UP" if pct > 5 else "DOWN" if pct < -5 else "STABLE",
                }
        return comparison

    # ── ACTION: apply_budget_rule ─────────────────────────────────────────
    def _apply_budget_rule(self, totals):
        total = sum(totals.values())
        if not total:
            return {}
        buckets = {"Needs": 0.0, "Wants": 0.0, "Savings": 0.0, "Other": 0.0}
        for cat, amt in totals.items():
            placed = False
            for bucket, cats in BUDGET_MAPPING.items():
                if cat in cats:
                    buckets[bucket] += amt
                    placed = True
                    break
            if not placed:
                buckets["Other"] += amt
        targets = {"Needs": 50, "Wants": 30, "Savings": 20, "Other": 0}
        return {
            b: {"amount": round(a, 2), "pct": round(a/total*100, 1),
                "target_pct": targets[b]}
            for b, a in buckets.items()
        }

    # ── ACTION: update_history ────────────────────────────────────────────
    def _update_history(self, totals):
        self.agent.spending_history = totals


# ── Agent ─────────────────────────────────────────────────────────────────────
class AnalyzerAgent(Agent):

    def __init__(self, jid, password, advisor_jid):
        super().__init__(jid, password)
        self.advisor_jid      = advisor_jid
        self.spending_history = {}   # Belief: historical category totals
        self.corrections      = {}   # Belief: user category corrections

    async def setup(self):
        print(f"[AnalyzerAgent] Agent started: {self.jid}")
        self.add_behaviour(AnalyzeBehaviour())
