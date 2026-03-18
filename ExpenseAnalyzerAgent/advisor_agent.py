"""
ADVISOR AGENT  (SPADE)
----------------------
JID      : advisor_agent@localhost
Behaviour: CyclicBehaviour — waits for analysis_results and user_query messages,
           generates recommendations and reports, answers queries.

Prometheus Percepts : analysis_complete, user_query, user_goal_set
Prometheus Actions  : generate_report, apply_50_30_20_rule,
                      generate_recommendations, answer_query, present_output
"""

import json
import asyncio

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


SAVINGS_TIPS = {
    "Food & Dining":  ["Cook at home 3+ more days per week to reduce food costs significantly.",
                       "Meal-prep on Sundays to cut impulse food purchases during the week."],
    "Transport":      ["Use public transport (trotro) for routine commutes instead of ride-hailing.",
                       "Combine errands into one trip to reduce fuel or ride costs."],
    "Entertainment":  ["Audit your streaming subscriptions — cancel unused ones immediately.",
                       "Switch to a shared family plan for streaming services to split costs."],
    "Shopping":       ["Apply a 48-hour rule before any non-essential purchase.",
                       "Create a shopping list and stick to it strictly."],
    "Utilities":      ["Unplug appliances when not in use to reduce electricity bills.",
                       "Compare telecom bundles and switch to the most cost-effective plan."],
    "Other":          ["Track daily spending for one week to identify hidden cost leaks.",
                       "Review uncategorized transactions manually to find patterns."],
}


# ── Behaviour ─────────────────────────────────────────────────────────────────
class AdviseBehaviour(CyclicBehaviour):
    """
    Receives analysis_results and user_query messages.
    Produces recommendations, reports, and query answers.
    """

    async def run(self):
        msg = await self.receive(timeout=30)
        if msg is None:
            return

        ontology = msg.get_metadata("ontology")

        # ── PERCEPT: analysis_complete ────────────────────────────────────
        if ontology == "analysis_results":
            analysis = json.loads(msg.body)
            print(f"[AdvisorAgent] Received analysis_results "
                  f"({analysis['transaction_count']} transactions)")

            # ACTION: generate_recommendations + generate_report
            recommendations = self._generate_recommendations(analysis)
            report          = self._generate_report(analysis, recommendations)

            # Store for query access
            self.agent.last_analysis = analysis
            self.agent.last_report   = report

            # ACTION: present_output — print summary to console
            self._print_report(report)

        # ── PERCEPT: user_query ───────────────────────────────────────────
        elif ontology == "user_query":
            data     = json.loads(msg.body)
            question = data.get("query", "")
            analysis = self.agent.last_analysis

            if not analysis:
                answer = "No analysis data available. Please run an analysis first."
            else:
                answer = self._answer_query(question, analysis)

            print(f"\n[AdvisorAgent] Query: '{question}'")
            print(f"[AdvisorAgent] Answer: {answer}\n")

            # Send answer back to requester
            reply = Message(to=str(msg.sender))
            reply.set_metadata("performative", "inform")
            reply.set_metadata("ontology", "query_response")
            reply.body = json.dumps({"answer": answer})
            await self.send(reply)

        # ── PERCEPT: user_goal_set ────────────────────────────────────────
        elif ontology == "user_goal":
            data = json.loads(msg.body)
            self.agent.user_goal = data
            print(f"[AdvisorAgent] Savings goal set: GHS {data.get('savings_target')}")

    # ── ACTION: generate_recommendations ─────────────────────────────────
    def _generate_recommendations(self, analysis):
        recs         = []
        budget       = analysis.get("budget_analysis", {})
        totals       = analysis.get("category_totals", {})
        total_spend  = analysis.get("total_spend", 0)
        subs         = analysis.get("subscriptions", [])

        # 1. Budget rule violations
        for bucket, data in budget.items():
            if bucket == "Other":
                continue
            target = data.get("target_pct", 0)
            actual = data.get("pct", 0)
            if target > 0 and actual > target:
                overage = round(actual - target, 1)
                recs.append({
                    "priority": "HIGH",
                    "type":     "budget_violation",
                    "title":    f"{bucket} spending is {overage}% over target",
                    "detail":   (f"You spent {actual}% on {bucket} but the 50/30/20 rule "
                                 f"recommends {target}%. Reduce by approx. "
                                 f"GHS {round((overage/100)*total_spend,2)}/month."),
                    "savings":  round((overage/100)*total_spend, 2),
                })

        # 2. Category-specific tips for top 3
        for cat in list(totals.keys())[:3]:
            tips = SAVINGS_TIPS.get(cat, SAVINGS_TIPS["Other"])
            recs.append({"priority":"MEDIUM","type":"category_tip",
                         "title":f"Reduce {cat} spending","detail":tips[0],"savings":None})

        # 3. Subscription alert
        if subs:
            total_sub = sum(s["monthly_cost"] for s in subs)
            recs.append({
                "priority": "MEDIUM",
                "type":     "subscription_alert",
                "title":    f"{len(subs)} recurring charge(s) detected",
                "detail":   (f"Total: GHS {round(total_sub,2)}/month "
                             f"(GHS {round(total_sub*12,2)}/year). "
                             "Cancel any unused subscriptions."),
                "savings":  round(total_sub, 2),
            })

        # 4. Savings goal gap
        goal = self.agent.user_goal
        if goal:
            target = goal.get("savings_target", 0)
            saved  = budget.get("Savings", {}).get("amount", 0)
            gap    = target - saved
            if gap > 0:
                recs.append({
                    "priority": "HIGH",
                    "type":     "goal_gap",
                    "title":    f"GHS {round(gap,2)} short of savings goal",
                    "detail":   (f"Target: GHS {target}/month. "
                                 f"Current: GHS {round(saved,2)}. "
                                 f"Cut GHS {round(gap,2)} from Wants to close the gap."),
                    "savings":  round(gap, 2),
                })

        recs.sort(key=lambda r: 0 if r["priority"] == "HIGH" else 1)
        return recs

    # ── ACTION: generate_report ───────────────────────────────────────────
    def _generate_report(self, analysis, recommendations):
        budget      = analysis.get("budget_analysis", {})
        total_spend = analysis.get("total_spend", 0)
        savings_pot = sum(r["savings"] for r in recommendations if r.get("savings"))
        return {
            "summary": {
                "total_spend":        total_spend,
                "transaction_count":  analysis.get("transaction_count", 0),
                "top_category":       list(analysis.get("category_totals", {}).keys())[0]
                                      if analysis.get("category_totals") else "N/A",
                "savings_potential":  round(savings_pot, 2),
                "anomaly_count":      len(analysis.get("anomalies", [])),
                "subscription_count": len(analysis.get("subscriptions", [])),
            },
            "category_totals":   analysis.get("category_totals", {}),
            "budget_analysis":   budget,
            "anomalies":         analysis.get("anomalies", []),
            "subscriptions":     analysis.get("subscriptions", []),
            "period_comparison": analysis.get("period_comparison", {}),
            "recommendations":   recommendations,
            "transactions":      analysis.get("transactions", []),
        }

    # ── ACTION: answer_query ──────────────────────────────────────────────
    def _answer_query(self, query, analysis):
        q      = query.lower()
        totals = analysis.get("category_totals", {})
        total  = analysis.get("total_spend", 0)

        if any(w in q for w in ["most","highest","top","biggest"]):
            if totals:
                cat = list(totals.keys())[0]
                return (f"Your highest spending category is {cat} at GHS {totals[cat]:.2f}, "
                        f"which is {round(totals[cat]/total*100,1)}% of total spend.")

        if any(w in q for w in ["total","overall","altogether","spent"]):
            return (f"Your total spending is GHS {total:.2f} across "
                    f"{analysis.get('transaction_count',0)} transactions.")

        for cat in totals:
            if cat.lower() in q:
                pct = round(totals[cat]/total*100,1) if total else 0
                return (f"You spent GHS {totals[cat]:.2f} on {cat}, "
                        f"which is {pct}% of your total spending.")

        if any(w in q for w in ["sav","save","saving"]):
            saved = analysis.get("budget_analysis",{}).get("Savings",{}).get("amount",0)
            pct   = analysis.get("budget_analysis",{}).get("Savings",{}).get("pct",0)
            return (f"You saved GHS {saved:.2f} ({pct}% of spending). "
                    "The 50/30/20 rule recommends saving at least 20%.")

        if any(w in q for w in ["unusual","anomal","strange","suspicious"]):
            anomalies = analysis.get("anomalies", [])
            if anomalies:
                return (f"{len(anomalies)} unusual transaction(s) detected. "
                        f"Largest: '{anomalies[0]['description']}' "
                        f"for GHS {anomalies[0]['amount']:.2f}.")
            return "No unusual transactions detected."

        if any(w in q for w in ["subscript","recurring","monthly charge"]):
            subs = analysis.get("subscriptions", [])
            if subs:
                return (f"{len(subs)} recurring charge(s) totalling "
                        f"GHS {sum(s['monthly_cost'] for s in subs):.2f}/month.")
            return "No recurring subscriptions detected."

        return ("I can answer questions about total spending, categories, "
                "savings, anomalies, or subscriptions.")

    # ── ACTION: present_output ────────────────────────────────────────────
    def _print_report(self, report):
        s = report["summary"]
        print("\n" + "="*55)
        print("  EXPENSE ANALYZER AGENT — REPORT")
        print("="*55)
        print(f"  Total Spend       : GHS {s['total_spend']:,.2f}")
        print(f"  Transactions      : {s['transaction_count']}")
        print(f"  Top Category      : {s['top_category']}")
        print(f"  Anomalies Found   : {s['anomaly_count']}")
        print(f"  Subscriptions     : {s['subscription_count']}")
        print(f"  Savings Potential : GHS {s['savings_potential']:,.2f}")
        print("-"*55)
        print("  CATEGORY BREAKDOWN")
        for cat, amt in report["category_totals"].items():
            print(f"    {cat:<25} GHS {amt:>8,.2f}")
        print("-"*55)
        print("  BUDGET (50/30/20)")
        for bucket, data in report["budget_analysis"].items():
            marker = "!!" if data["pct"] > data["target_pct"] + 3 else "  "
            print(f"  {marker} {bucket:<10} {data['pct']:>5.1f}%  "
                  f"(target {data['target_pct']}%)  GHS {data['amount']:,.2f}")
        print("-"*55)
        print("  RECOMMENDATIONS")
        for i, r in enumerate(report["recommendations"], 1):
            print(f"  [{r['priority']}] {r['title']}")
            print(f"       {r['detail'][:70]}...")
        if report["anomalies"]:
            print("-"*55)
            print("  ANOMALIES")
            for a in report["anomalies"]:
                print(f"  !! {a['description']:<30} GHS {a['amount']:>8,.2f}  "
                      f"(Z={a['z_score']})")
        if report["subscriptions"]:
            print("-"*55)
            print("  SUBSCRIPTIONS")
            for s in report["subscriptions"]:
                print(f"  ~~ {s['description']:<30} GHS {s['monthly_cost']:>6,.2f}/mo")
        print("="*55 + "\n")


# ── Agent ─────────────────────────────────────────────────────────────────────
class AdvisorAgent(Agent):

    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.last_analysis = None
        self.last_report   = None
        self.user_goal     = None    # Belief: savings target

    async def setup(self):
        print(f"[AdvisorAgent] Agent started: {self.jid}")
        self.add_behaviour(AdviseBehaviour())
