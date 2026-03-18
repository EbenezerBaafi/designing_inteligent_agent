# Personal Expense Analyzer Agent
## DCIT 403 Semester Project — Phase 5 (SPADE Implementation)

---

## Prerequisites

### 1. Install Python Dependencies
```bash
pip install spade
```

### 2. Set Up ejabberd XMPP Server

If ejabberd is not installed:
```bash
# Ubuntu / Debian
sudo apt-get install ejabberd

# macOS
brew install ejabberd
```

Start ejabberd:
```bash
sudo ejabberdctl start
```

### 3. Create XMPP Agent Accounts

Register the three agent accounts on your ejabberd server:

```bash
sudo ejabberdctl register input_agent    localhost input123
sudo ejabberdctl register analyzer_agent localhost analyzer123
sudo ejabberdctl register advisor_agent  localhost advisor123
```

Verify accounts exist:
```bash
sudo ejabberdctl registered_users localhost
```

---

## Project Structure

```
expense_spade/
├── main.py                  # Entry point — starts all agents + runs simulation
├── agents/
│   ├── input_agent.py       # INPUT AGENT     — perceive, validate, normalize
│   ├── analyzer_agent.py    # ANALYZER AGENT  — categorize, detect, compare
│   └── advisor_agent.py     # ADVISOR AGENT   — recommend, report, answer queries
├── sample_transactions.csv  # Test data
└── README.md
```

---

## Run the Simulation

```bash
# With sample data (built-in 30 transactions)
python main.py

# With your own CSV file
python main.py --file sample_transactions.csv
```

### CSV Format
```csv
date,description,amount
2025-03-01,KFC Lunch,85.00
2025-03-02,Uber Ride,45.00
2025-03-03,Netflix Subscription,55.00
```

---

## How It Maps to Prometheus Design

| Prometheus Concept  | SPADE Implementation                                      |
|---------------------|-----------------------------------------------------------|
| Agent               | `spade.agent.Agent` subclass                              |
| Percept             | Method named `perceive_*` on each Agent class             |
| Action              | Private method `_action_name` inside a Behaviour          |
| Belief              | Instance attribute on the Agent (e.g. `spending_history`) |
| Plan                | Ordered logic inside a `Behaviour.run()` method           |
| Message             | `spade.message.Message` with `ontology` metadata          |
| Behaviour           | `OneShotBehaviour` (InputAgent) / `CyclicBehaviour` (Analyzer, Advisor) |

---

## Agent Communication Flow

```
main.py
  |
  |-- perceive_manual(transactions)
  |        |
  v        v
InputAgent (OneShotBehaviour)
  | ParseAndForwardBehaviour.run()
  | MESSAGE: parsed_transactions  -->  AnalyzerAgent
                                           |
                                           | AnalyzeBehaviour.run()
                                           | categorize -> detect -> subscribe -> compare
                                           | MESSAGE: analysis_results  -->  AdvisorAgent
                                                                                 |
                                                                                 | AdviseBehaviour.run()
                                                                                 | generate_report
                                                                                 | generate_recommendations
                                                                                 | print_report()

main.py  -->  MESSAGE: user_query  -->  AdvisorAgent
                                           |
                                           | answer_query()
                                           | MESSAGE: query_response  -->  sender
```

---

## XMPP Message Ontologies

| Ontology              | Sender          | Receiver        | Content                              |
|-----------------------|-----------------|-----------------|--------------------------------------|
| `parsed_transactions` | InputAgent      | AnalyzerAgent   | rows[], row_count, validation_status |
| `analysis_results`    | AnalyzerAgent   | AdvisorAgent    | totals, anomalies, subscriptions     |
| `user_query`          | main / user     | AdvisorAgent    | query: str                           |
| `query_response`      | AdvisorAgent    | requester       | answer: str                          |
| `user_goal`           | main / user     | AdvisorAgent    | savings_target, income               |
| `category_correction` | main / user     | AnalyzerAgent   | description, category                |
| `category_data`       | AnalyzerAgent   | AdvisorAgent    | category, total                      |

---

## Troubleshooting

**Connection refused**: Make sure ejabberd is running (`sudo ejabberdctl status`)

**Authentication failed**: Re-register accounts with correct passwords

**Agents don't respond**: Increase `asyncio.sleep()` wait times in `main.py`

**SSL errors**: Add `verify_security=False` to `agent.start()` for local dev:
```python
await input_agent.start(auto_register=True)
```
or edit ejabberd.yml to disable TLS for localhost.
