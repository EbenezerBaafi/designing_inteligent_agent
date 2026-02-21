"""
LAB 3: GOALS, EVENTS, AND REACTIVE BEHAVIOR
============================================

Objective: Model agent goals and event-triggered behavior using FSM

This lab demonstrates:
1. Rescue and response goals for disaster management
2. Event-triggered behavior from sensor reports
3. Finite State Machine (FSM) implementation for reactive agents

"""

import spade
import asyncio
import logging
import random
import json
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, PeriodicBehaviour
from spade.message import Message
from spade.template import Template

# Create logs directory
LOGS_DIR = Path("lab3_logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging
log_filename = LOGS_DIR / f"lab3_execution_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# PART 1: DISASTER EVENT MODEL (from Lab 2)
# ============================================================================

class DisasterType(Enum):
    """Types of disasters"""
    EARTHQUAKE = "Earthquake"
    FLOOD = "Flood"
    FIRE = "Fire"
    HURRICANE = "Hurricane"


class SeverityLevel(Enum):
    """Severity levels for disasters"""
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5


@dataclass
class DisasterEvent:
    """Represents a disaster event"""
    event_id: str
    disaster_type: DisasterType
    severity: SeverityLevel
    location: str
    timestamp: str
    affected_area_km2: float
    casualties_estimated: int


# ============================================================================
# PART 2: AGENT GOALS DEFINITION
# ============================================================================

class RescueGoal(Enum):
    """Rescue and response goals for disaster management"""
    ASSESS_SITUATION = "Assess disaster situation"
    DEPLOY_RESOURCES = "Deploy rescue resources"
    EVACUATE_CIVILIANS = "Evacuate affected civilians"
    PROVIDE_MEDICAL_AID = "Provide medical assistance"
    RESTORE_INFRASTRUCTURE = "Restore critical infrastructure"
    MONITOR_RECOVERY = "Monitor recovery progress"


@dataclass
class Goal:
    """Represents an agent goal"""
    goal_id: str
    goal_type: RescueGoal
    priority: int  # 1-5, 5 being highest
    status: str  # "pending", "active", "completed", "failed"
    created_at: str
    completed_at: str = None
    
    def to_dict(self) -> Dict:
        return {
            'goal_id': self.goal_id,
            'goal_type': self.goal_type.value,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at
        }


# ============================================================================
# PART 3: FSM STATES FOR RESPONSE AGENT
# ============================================================================

# FSM State names
STATE_IDLE = "IDLE"
STATE_ANALYZING = "ANALYZING"
STATE_PLANNING = "PLANNING"
STATE_RESPONDING = "RESPONDING"
STATE_MONITORING = "MONITORING"
STATE_COMPLETED = "COMPLETED"


class ResponseAgentFSM(FSMBehaviour):
    """
    Finite State Machine for disaster response agent
    
    State Transitions:
    IDLE → ANALYZING → PLANNING → RESPONDING → MONITORING → COMPLETED
           ↑______________|                        |
                                                   ↓
                                                 IDLE (new event)
    """
    pass


class IdleState(State):
    """
    IDLE State: Waiting for disaster events
    """
    async def run(self):
        logger.info(f"\n[{self.agent.name}] 💤 STATE: IDLE - Waiting for disaster alerts...")
        
        # Wait for incoming disaster alert message
        msg = await self.receive(timeout=5)
        
        if msg:
            logger.warning(f"[{self.agent.name}] 🚨 ALERT RECEIVED!")
            
            # Parse disaster event from message
            try:
                event_data = json.loads(msg.body)
                self.agent.current_event = event_data
                self.agent.fsm_trace.append({
                    'state': STATE_IDLE,
                    'timestamp': datetime.now().isoformat(),
                    'action': 'Received disaster alert',
                    'event_id': event_data.get('event_id', 'UNKNOWN')
                })
                
                logger.info(f"[{self.agent.name}] 📩 Event: {event_data.get('disaster_type')} "
                          f"(Severity: {event_data.get('severity_name')})")
                
                # Transition to ANALYZING state
                self.set_next_state(STATE_ANALYZING)
            except json.JSONDecodeError:
                logger.error(f"[{self.agent.name}] ❌ Failed to parse event data")
                self.set_next_state(STATE_IDLE)
        else:
            # No message, stay idle
            self.set_next_state(STATE_IDLE)


class AnalyzingState(State):
    """
    ANALYZING State: Assess the disaster situation
    """
    async def run(self):
        logger.info(f"\n[{self.agent.name}] 🔍 STATE: ANALYZING - Assessing disaster situation...")
        
        event = self.agent.current_event
        severity = event.get('severity', 1)
        disaster_type = event.get('disaster_type', 'Unknown')
        
        # Simulate analysis time
        await asyncio.sleep(1)
        
        # Create assessment goal
        goal = Goal(
            goal_id=f"GOAL-{len(self.agent.goals) + 1:03d}",
            goal_type=RescueGoal.ASSESS_SITUATION,
            priority=5,
            status="active",
            created_at=datetime.now().isoformat()
        )
        self.agent.goals.append(goal)
        
        logger.info(f"[{self.agent.name}] 📊 Analysis Complete:")
        logger.info(f"  - Disaster Type: {disaster_type}")
        logger.info(f"  - Severity Level: {severity}/5")
        logger.info(f"  - Affected Area: {event.get('affected_area_km2', 0)} km²")
        logger.info(f"  - Estimated Casualties: {event.get('casualties_estimated', 0)}")
        
        # Mark assessment goal as completed
        goal.status = "completed"
        goal.completed_at = datetime.now().isoformat()
        
        self.agent.fsm_trace.append({
            'state': STATE_ANALYZING,
            'timestamp': datetime.now().isoformat(),
            'action': 'Completed situation assessment',
            'severity': severity
        })
        
        # Transition to PLANNING state
        self.set_next_state(STATE_PLANNING)


class PlanningState(State):
    """
    PLANNING State: Create response plan and define goals
    """
    async def run(self):
        logger.info(f"\n[{self.agent.name}] 📋 STATE: PLANNING - Creating response plan...")
        
        event = self.agent.current_event
        severity = event.get('severity', 1)
        
        # Simulate planning time
        await asyncio.sleep(1)
        
        # Generate goals based on severity
        response_goals = self._generate_response_goals(severity)
        
        logger.info(f"[{self.agent.name}] 🎯 Response Plan Created:")
        for i, goal in enumerate(response_goals, 1):
            self.agent.goals.append(goal)
            logger.info(f"  {i}. {goal.goal_type.value} (Priority: {goal.priority})")
        
        self.agent.fsm_trace.append({
            'state': STATE_PLANNING,
            'timestamp': datetime.now().isoformat(),
            'action': 'Response plan created',
            'goals_count': len(response_goals)
        })
        
        # Transition to RESPONDING state
        self.set_next_state(STATE_RESPONDING)
    
    def _generate_response_goals(self, severity: int) -> List[Goal]:
        """Generate response goals based on disaster severity"""
        goals = []
        goal_counter = len(self.agent.goals)
        
        # All disasters need these basic goals
        basic_goals = [
            (RescueGoal.DEPLOY_RESOURCES, 5),
            (RescueGoal.EVACUATE_CIVILIANS, 5),
        ]
        
        # Add goals based on severity
        if severity >= 3:
            basic_goals.append((RescueGoal.PROVIDE_MEDICAL_AID, 4))
        
        if severity >= 4:
            basic_goals.append((RescueGoal.RESTORE_INFRASTRUCTURE, 3))
        
        # Always add monitoring goal
        basic_goals.append((RescueGoal.MONITOR_RECOVERY, 2))
        
        # Create goal objects
        for goal_type, priority in basic_goals:
            goal_counter += 1
            goal = Goal(
                goal_id=f"GOAL-{goal_counter:03d}",
                goal_type=goal_type,
                priority=priority,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            goals.append(goal)
        
        return goals


class RespondingState(State):
    """
    RESPONDING State: Execute response actions
    """
    async def run(self):
        logger.info(f"\n[{self.agent.name}] 🚑 STATE: RESPONDING - Executing response actions...")
        
        # Get pending goals sorted by priority
        pending_goals = [g for g in self.agent.goals if g.status == "pending"]
        pending_goals.sort(key=lambda x: x.priority, reverse=True)
        
        # Execute goals
        for goal in pending_goals:
            logger.info(f"[{self.agent.name}] ⚡ Executing: {goal.goal_type.value}")
            
            # Simulate action execution
            await asyncio.sleep(0.5)
            
            # Update goal status
            goal.status = "completed"
            goal.completed_at = datetime.now().isoformat()
            
            logger.info(f"[{self.agent.name}] ✅ Completed: {goal.goal_type.value}")
        
        self.agent.fsm_trace.append({
            'state': STATE_RESPONDING,
            'timestamp': datetime.now().isoformat(),
            'action': 'Response actions executed',
            'goals_completed': len(pending_goals)
        })
        
        # Transition to MONITORING state
        self.set_next_state(STATE_MONITORING)


class MonitoringState(State):
    """
    MONITORING State: Monitor recovery and verify goals
    """
    async def run(self):
        logger.info(f"\n[{self.agent.name}] 📡 STATE: MONITORING - Monitoring recovery progress...")
        
        # Simulate monitoring
        await asyncio.sleep(1)
        
        # Check all goals
        total_goals = len(self.agent.goals)
        completed_goals = len([g for g in self.agent.goals if g.status == "completed"])
        
        logger.info(f"[{self.agent.name}] 📊 Goal Status:")
        logger.info(f"  - Total Goals: {total_goals}")
        logger.info(f"  - Completed: {completed_goals}")
        logger.info(f"  - Success Rate: {(completed_goals/total_goals)*100:.1f}%")
        
        self.agent.fsm_trace.append({
            'state': STATE_MONITORING,
            'timestamp': datetime.now().isoformat(),
            'action': 'Recovery monitoring completed',
            'goals_completed': completed_goals,
            'total_goals': total_goals
        })
        
        # Transition to COMPLETED state
        self.set_next_state(STATE_COMPLETED)


class CompletedState(State):
    """
    COMPLETED State: Response cycle finished
    """
    async def run(self):
        logger.info(f"\n[{self.agent.name}] 🏁 STATE: COMPLETED - Response cycle finished!")
        
        event = self.agent.current_event
        logger.info(f"[{self.agent.name}] ✅ Successfully responded to {event.get('event_id')}")
        
        # Generate response report
        self._generate_report()
        
        self.agent.fsm_trace.append({
            'state': STATE_COMPLETED,
            'timestamp': datetime.now().isoformat(),
            'action': 'Response cycle completed',
            'event_id': event.get('event_id')
        })
        
        # Clear current event
        self.agent.current_event = None
        
        # Return to IDLE state for next event
        logger.info(f"[{self.agent.name}] 🔄 Returning to IDLE state...")
        self.set_next_state(STATE_IDLE)
    
    def _generate_report(self):
        """Generate response summary report"""
        logger.info(f"\n{'='*70}")
        logger.info(f"[{self.agent.name}] 📄 RESPONSE SUMMARY REPORT")
        logger.info(f"{'='*70}")
        
        # Goals summary
        for goal in self.agent.goals:
            status_emoji = "✅" if goal.status == "completed" else "❌"
            logger.info(f"{status_emoji} {goal.goal_type.value} - Priority {goal.priority}")
        
        logger.info(f"{'='*70}\n")


# ============================================================================
# PART 4: RESPONSE AGENT IMPLEMENTATION
# ============================================================================

class ResponseAgent(Agent):
    """
    Response agent with FSM-based reactive behavior
    """
    
    async def setup(self):
        """Initialize the response agent"""
        logger.info(f"\n{'='*70}")
        logger.info(f"[SETUP] Initializing ResponseAgent: {self.jid}")
        logger.info(f"{'='*70}\n")
        
        self.name = "ResponseAgent"
        self.current_event = None
        self.goals: List[Goal] = []
        self.fsm_trace: List[Dict] = []
        
        # Create FSM
        fsm = ResponseAgentFSM()
        
        # Add states
        fsm.add_state(name=STATE_IDLE, state=IdleState(), initial=True)
        fsm.add_state(name=STATE_ANALYZING, state=AnalyzingState())
        fsm.add_state(name=STATE_PLANNING, state=PlanningState())
        fsm.add_state(name=STATE_RESPONDING, state=RespondingState())
        fsm.add_state(name=STATE_MONITORING, state=MonitoringState())
        fsm.add_state(name=STATE_COMPLETED, state=CompletedState())
        
        # Add transitions
        fsm.add_transition(source=STATE_IDLE, dest=STATE_IDLE)
        fsm.add_transition(source=STATE_IDLE, dest=STATE_ANALYZING)
        fsm.add_transition(source=STATE_ANALYZING, dest=STATE_PLANNING)
        fsm.add_transition(source=STATE_PLANNING, dest=STATE_RESPONDING)
        fsm.add_transition(source=STATE_RESPONDING, dest=STATE_MONITORING)
        fsm.add_transition(source=STATE_MONITORING, dest=STATE_COMPLETED)
        fsm.add_transition(source=STATE_COMPLETED, dest=STATE_IDLE)
        
        # Add FSM behaviour
        template = Template()
        template.set_metadata("performative", "inform")
        self.add_behaviour(fsm, template)
        
        logger.info(f"✅ ResponseAgent initialized with FSM")
        logger.info(f"📊 FSM States: {STATE_IDLE} → {STATE_ANALYZING} → {STATE_PLANNING} → "
                   f"{STATE_RESPONDING} → {STATE_MONITORING} → {STATE_COMPLETED}")
        logger.info(f"📁 Execution trace: {log_filename}\n")
    
    def export_fsm_trace(self, filename: Path):
        """Export FSM execution trace to JSON"""
        data = {
            'agent': str(self.jid),
            'session_start': datetime.now().isoformat(),
            'total_states_visited': len(self.fsm_trace),
            'goals_created': len(self.goals),
            'trace': self.fsm_trace,
            'goals': [g.to_dict() for g in self.goals]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✅ Exported FSM trace to {filename}")


# ============================================================================
# PART 5: SENSOR AGENT (Event Generator)
# ============================================================================

class SensorAgent(Agent):
    """
    Sensor agent that detects disasters and triggers response
    """
    
    class DisasterDetectionBehaviour(PeriodicBehaviour):
        """Periodically generates disaster events"""
        
        async def run(self):
            # Randomly generate disaster (30% chance)
            if random.random() < 0.3:
                event = self._generate_disaster_event()
                
                logger.warning(f"\n{'='*70}")
                logger.warning(f"[SensorAgent] 🚨 DISASTER DETECTED!")
                logger.warning(f"{'='*70}")
                logger.warning(f"Event ID: {event['event_id']}")
                logger.warning(f"Type: {event['disaster_type']}")
                logger.warning(f"Severity: {event['severity_name']} (Level {event['severity']}/5)")
                logger.warning(f"Location: {event['location']}")
                logger.warning(f"{'='*70}\n")
                
                # Send disaster alert to response agent
                msg = Message(to=self.agent.response_agent_jid)
                msg.set_metadata("performative", "inform")
                msg.body = json.dumps(event)
                
                await self.send(msg)
                logger.info(f"[SensorAgent] 📤 Alert sent to ResponseAgent\n")
        
        def _generate_disaster_event(self) -> Dict:
            """Generate a random disaster event"""
            self.agent.event_counter += 1
            
            disaster_type = random.choice([
                DisasterType.EARTHQUAKE,
                DisasterType.FLOOD,
                DisasterType.FIRE,
                DisasterType.HURRICANE
            ])
            
            severity = random.choice(list(SeverityLevel))
            
            return {
                'event_id': f"EVENT-{self.agent.event_counter:04d}",
                'disaster_type': disaster_type.value,
                'severity': severity.value,
                'severity_name': severity.name,
                'location': "Disaster Zone Alpha",
                'timestamp': datetime.now().isoformat(),
                'affected_area_km2': severity.value * random.uniform(20, 100),
                'casualties_estimated': severity.value * random.randint(10, 200)
            }
    
    async def setup(self):
        """Initialize sensor agent"""
        logger.info(f"[SETUP] Initializing SensorAgent: {self.jid}\n")
        
        self.event_counter = 0
        self.response_agent_jid = "response@localhost"
        
        # Add disaster detection behaviour (every 5 seconds)
        detector = self.DisasterDetectionBehaviour(period=5)
        self.add_behaviour(detector)
        
        logger.info(f"✅ SensorAgent initialized")
        logger.info(f"🔍 Monitoring for disasters every 5 seconds\n")


# ============================================================================
# PART 6: MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("\n" + "="*70)
    print("LAB 3: GOALS, EVENTS, AND REACTIVE BEHAVIOR")
    print("Finite State Machine for Disaster Response")
    print("="*70 + "\n")
    
    # Agent credentials
    SENSOR_JID = "sensor@localhost"
    SENSOR_PASSWORD = "password123"
    RESPONSE_JID = "response@localhost"
    RESPONSE_PASSWORD = "password123"
    
    print("🤖 Creating Agents...")
    print(f"   Sensor Agent: {SENSOR_JID}")
    print(f"   Response Agent: {RESPONSE_JID}")
    print(f"📁 Log Directory: {LOGS_DIR.absolute()}\n")
    
    # Create agents
    sensor_agent = SensorAgent(SENSOR_JID, SENSOR_PASSWORD)
    response_agent = ResponseAgent(RESPONSE_JID, RESPONSE_PASSWORD)
    
    try:
        print("🚀 Starting Agents...")
        await response_agent.start(auto_register=True)
        await sensor_agent.start(auto_register=True)
        print("✅ Both agents are now active\n")
        
        print("⏱️  Running for 40 seconds...")
        print("💡 Watch for disaster alerts and FSM state transitions!\n")
        
        # Let agents run
        await asyncio.sleep(40)
        
        print("\n" + "="*70)
        print("🛑 Shutting down agents...")
        print("📊 Generating final reports...")
        
        # Export FSM trace
        trace_file = LOGS_DIR / f"fsm_execution_trace_{session_timestamp}.json"
        response_agent.export_fsm_trace(trace_file)
        
        await sensor_agent.stop()
        await response_agent.stop()
        
        # Final summary
        print("\n" + "="*70)
        print("📋 LAB 3 SUMMARY")
        print("="*70)
        print(f"Total Goals Created: {len(response_agent.goals)}")
        print(f"Goals Completed: {len([g for g in response_agent.goals if g.status == 'completed'])}")
        print(f"FSM States Visited: {len(response_agent.fsm_trace)}")
        
        print("\n" + "="*70)
        print("📁 DELIVERABLES GENERATED")
        print("="*70)
        print(f"1. Execution Trace (Log): {log_filename}")
        print(f"2. FSM Trace (JSON): {trace_file}")
        print(f"3. FSM Diagram: See LAB3_FSM_DIAGRAM.md")
        print("\n💡 Submit these files to your instructor!")
        
        print("\n" + "="*70)
        print("✅ Lab 3 Complete!")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure ejabberd is running: sudo systemctl start ejabberd")
        print("  2. Create credentials:")
        print("     sudo ejabberdctl register sensor localhost password123")
        print("     sudo ejabberdctl register response localhost password123")
        return False
    
    return True


if __name__ == "__main__":
    spade.run(main())
