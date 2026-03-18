"""
main.py — SPADE Expense Analyzer Agent Simulation
DCIT 403 Semester Project | Phase 5 Prototype

Usage:
    python main.py                  # Run full simulation with sample data
    python main.py --file data.csv  # Run with a CSV file

XMPP Accounts Required (create these on your ejabberd server):
    input_agent@localhost    password: input123
    analyzer_agent@localhost password: analyzer123
    advisor_agent@localhost  password: advisor123
"""
import sys
import asyncio
import argparse
import csv
import io
import json
import time

import spade
from spade.message import Message

from agents.input_agent    import InputAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.advisor_agent  import AdvisorAgent

# ── XMPP Configuration ────────────────────────────────────────────────────────
XMPP_HOST = "localhost"

AGENT_JIDS = {
    "input":    f"input_agent@{XMPP_HOST}",
    "analyzer": f"analyzer_agent@{XMPP_HOST}",
    "advisor":  f"advisor_agent@{XMPP_HOST}",
}

AGENT_PASSWORDS = {
    "input":    "input123",
    "analyzer": "analyzer123",
    "advisor":  "advisor123",
}

# ── Sample Data ───────────────────────────────────────────────────────────────
SAMPLE_TRANSACTIONS = [
    {"date":"2025-03-01","description":"Shoprite Grocery","amount":"320.50"},
    {"date":"2025-03-02","description":"Uber Ride","amount":"45.00"},
    {"date":"2025-03-03","description":"Netflix Subscription","amount":"55.00"},
    {"date":"2025-03-05","description":"ECG Prepaid","amount":"200.00"},
    {"date":"2025-03-06","description":"KFC Lunch","amount":"85.00"},
    {"date":"2025-03-07","description":"Bolt Ride","amount":"38.00"},
    {"date":"2025-03-08","description":"Pharmacy Drugs","amount":"120.00"},
    {"date":"2025-03-09","description":"MTN Data Bundle","amount":"50.00"},
    {"date":"2025-03-10","description":"Restaurant Dinner","amount":"210.00"},
    {"date":"2025-03-11","description":"Shoprite Grocery","amount":"295.00"},
    {"date":"2025-03-12","description":"Netflix Subscription","amount":"55.00"},
    {"date":"2025-03-13","description":"Clothing Store","amount":"480.00"},
    {"date":"2025-03-14","description":"Uber Ride","amount":"52.00"},
    {"date":"2025-03-15","description":"Waakye Chop Bar","amount":"35.00"},
    {"date":"2025-03-16","description":"Spotify Subscription","amount":"30.00"},
    {"date":"2025-03-17","description":"Trotro Transport","amount":"15.00"},
    {"date":"2025-03-18","description":"Rent Payment","amount":"1200.00"},
    {"date":"2025-03-19","description":"Palace Mall Shopping","amount":"950.00"},  # anomaly
    {"date":"2025-03-20","description":"MTN Data Bundle","amount":"50.00"},
    {"date":"2025-03-21","description":"Bolt Ride","amount":"40.00"},
    {"date":"2025-03-22","description":"Shoprite Grocery","amount":"310.00"},
    {"date":"2025-03-23","description":"Susu Savings","amount":"200.00"},
    {"date":"2025-03-24","description":"Hospital Visit","amount":"180.00"},
    {"date":"2025-03-25","description":"Pizza Restaurant","amount":"95.00"},
    {"date":"2025-03-26","description":"Fuel Petrol","amount":"220.00"},
    {"date":"2025-03-27","description":"Spotify Subscription","amount":"30.00"},
    {"date":"2025-03-28","description":"Book Purchase","amount":"75.00"},
    {"date":"2025-03-29","description":"Uber Ride","amount":"60.00"},
    {"date":"2025-03-30","description":"Electricity ECG","amount":"180.00"},
    {"date":"2025-03-31","description":"Canteen Lunch","amount":"28.00"},
]


async def run_simulation(transactions, source="sample_data"):
    """Start all three agents and run the full analysis pipeline."""

    print("\n" + "="*55)
    print("  DCIT 403 — EXPENSE ANALYZER AGENT (SPADE)")
    print("  Starting multi-agent system...")
    print("="*55 + "\n")

    # ── Instantiate agents ────────────────────────────────────────────────
    input_agent    = InputAgent(
        AGENT_JIDS["input"],
        AGENT_PASSWORDS["input"],
        AGENT_JIDS["analyzer"]
    )
    analyzer_agent = AnalyzerAgent(
        AGENT_JIDS["analyzer"],
        AGENT_PASSWORDS["analyzer"],
        AGENT_JIDS["advisor"]
    )
    advisor_agent  = AdvisorAgent(
        AGENT_JIDS["advisor"],
        AGENT_PASSWORDS["advisor"]
    )

    # ── Start agents ──────────────────────────────────────────────────────
    await input_agent.start(auto_register=True)
    await analyzer_agent.start(auto_register=True)
    await advisor_agent.start(auto_register=True)
    print("[Main] All agents started. Waiting for registration...\n")
    await asyncio.sleep(3)

    # ── Set a savings goal on the AdvisorAgent ────────────────────────────
    goal_msg = Message(to=AGENT_JIDS["advisor"])
    goal_msg.set_metadata("performative", "inform")
    goal_msg.set_metadata("ontology", "user_goal")
    goal_msg.body = json.dumps({"savings_target": 500.0, "income": 3000.0})
    await input_agent.send_message(goal_msg)
    await asyncio.sleep(1)

    # ── PERCEPT: load transactions into InputAgent ─────────────────────
    input_agent.perceive_manual(transactions)
    input_agent.pending_source = source

    # ── Trigger analysis pipeline ─────────────────────────────────────────
    print("[Main] Triggering analysis pipeline...\n")
    input_agent.trigger_analysis()

    # Wait for full pipeline to complete
    await asyncio.sleep(8)

    # ── Demo: send a natural language query ───────────────────────────────
    print("[Main] Sending a natural language query to AdvisorAgent...")
    query_msg = Message(to=AGENT_JIDS["advisor"])
    query_msg.set_metadata("performative", "query-if")
    query_msg.set_metadata("ontology", "user_query")
    query_msg.body = json.dumps({"query": "How much did I spend on food?"})
    await input_agent.send_message(query_msg)
    await asyncio.sleep(3)

    # ── Demo: send a category correction ─────────────────────────────────
    print("[Main] Sending a category correction to AnalyzerAgent...")
    correction_msg = Message(to=AGENT_JIDS["analyzer"])
    correction_msg.set_metadata("performative", "inform")
    correction_msg.set_metadata("ontology", "category_correction")
    correction_msg.body = json.dumps({
        "description": "palace mall shopping",
        "category":    "Shopping"
    })
    await input_agent.send_message(correction_msg)
    await asyncio.sleep(2)

    # ── Stop all agents ───────────────────────────────────────────────────
    print("\n[Main] Simulation complete. Stopping agents...")
    await input_agent.stop()
    await analyzer_agent.stop()
    await advisor_agent.stop()
    print("[Main] All agents stopped.")


def load_csv(filepath):
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        return [{k.strip().lower(): v.strip() for k, v in row.items()}
                for row in reader]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPADE Expense Analyzer Agent")
    parser.add_argument("--file", help="Path to CSV file", default=None)
    args = parser.parse_args()

    if args.file:
        transactions = load_csv(args.file)
        source = args.file
    else:
        transactions = SAMPLE_TRANSACTIONS
        source = "sample_data"

    spade.run(run_simulation(transactions, source))
