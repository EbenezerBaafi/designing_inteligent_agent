"""
INPUT AGENT  (SPADE)
--------------------
JID      : input_agent@localhost
Behaviour: OneShotBehaviour — triggered once per analysis run

Prometheus Percepts : file_uploaded, manual_entry_submitted
Prometheus Actions  : read_file, validate_data, normalize_data, send_parsed_data
"""

import csv
import io
import json
import asyncio
from datetime import datetime

import spade
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y"]
REQUIRED_FIELDS = {"date", "description", "amount"}


# ── Behaviour ─────────────────────────────────────────────────────────────────
class ParseAndForwardBehaviour(OneShotBehaviour):
    """
    Perceive raw transaction data, validate, normalize,
    then send parsed_transactions message to Analyzer Agent.
    """

    async def run(self):
        raw_data = self.agent.pending_data
        source   = self.agent.pending_source

        print(f"[InputAgent] Received data from source: {source}")

        # ACTION: validate_data + normalize_data
        parsed = self._process_rows(raw_data, source)

        print(f"[InputAgent] Validated {parsed['row_count']} transactions "
              f"(errors: {len(parsed['errors'])})")

        # ACTION: send_parsed_data  →  AnalyzerAgent via XMPP message
        msg = Message(to=self.agent.analyzer_jid)
        msg.set_metadata("performative", "inform")
        msg.set_metadata("ontology", "parsed_transactions")
        msg.body = json.dumps(parsed)

        await self.send(msg)
        print(f"[InputAgent] Sent parsed_transactions to {self.agent.analyzer_jid}")

    # ── ACTION: validate_data ─────────────────────────────────────────────
    def _validate_row(self, row: dict, index: int, errors: list) -> bool:
        keys = set(row.keys())
        missing = REQUIRED_FIELDS - keys
        if missing:
            errors.append(f"Row {index}: missing fields {missing}")
            return False
        try:
            float(str(row.get("amount", "")).replace(",", "")
                  .replace("GHS", "").replace("₵", "").strip())
        except ValueError:
            errors.append(f"Row {index}: invalid amount '{row.get('amount')}'")
            return False
        return True

    # ── ACTION: normalize_data ────────────────────────────────────────────
    def _normalize_row(self, row: dict, warnings: list) -> dict:
        amount = float(
            str(row["amount"]).replace(",", "").replace("GHS", "")
            .replace("₵", "").strip()
        )
        parsed_date = None
        for fmt in DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(str(row["date"]).strip(), fmt)
                break
            except ValueError:
                continue
        if not parsed_date:
            warnings.append(f"Could not parse date '{row['date']}', using today.")
            parsed_date = datetime.today()

        return {
            "date":         parsed_date.strftime("%Y-%m-%d"),
            "month":        parsed_date.strftime("%Y-%m"),
            "description":  str(row.get("description", "")).strip(),
            "amount":       round(abs(amount), 2),
            "raw_category": str(row.get("category", "")).strip().lower(),
        }

    # ── ACTION: send_parsed_data (data prep) ─────────────────────────────
    def _process_rows(self, rows: list, source: str) -> dict:
        errors, warnings, valid = [], [], []
        for i, row in enumerate(rows, 1):
            if self._validate_row(row, i, errors):
                valid.append(self._normalize_row(row, warnings))
        return {
            "transactions":      valid,
            "row_count":         len(valid),
            "source":            source,
            "validation_status": len(errors) == 0,
            "errors":            errors,
            "warnings":          warnings,
        }


# ── Agent ─────────────────────────────────────────────────────────────────────
class InputAgent(Agent):

    def __init__(self, jid, password, analyzer_jid):
        super().__init__(jid, password)
        self.analyzer_jid  = analyzer_jid
        self.pending_data   = []
        self.pending_source = "unknown"

    # ── PERCEPT: file_uploaded ────────────────────────────────────────────
    def perceive_file(self, file_stream, filename: str):
        raw = file_stream.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))
        self.pending_data = [
            {k.strip().lower(): v.strip() for k, v in row.items()}
            for row in reader
        ]
        self.pending_source = filename

    # ── PERCEPT: manual_entry_submitted ──────────────────────────────────
    def perceive_manual(self, entries: list):
        self.pending_data   = entries
        self.pending_source = "manual_entry"

    async def setup(self):
        print(f"[InputAgent] Agent started: {self.jid}")

    def trigger_analysis(self):
        """Call after perceive_* to start the behaviour pipeline."""
        b = ParseAndForwardBehaviour()
        self.add_behaviour(b)
