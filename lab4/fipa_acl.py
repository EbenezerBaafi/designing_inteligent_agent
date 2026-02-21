#!/usr/bin/env python3
"""
LAB 4: AGENT COMMUNICATION USING FIPA-ACL

Objective: Enable inter-agent communication using FIPA-ACL

This lab demonstrates:
1. ACL message exchange between multiple agents
2. INFORM and REQUEST performatives
3. Message parsing and action triggering
4. Multi-agent coordination protocol

"""

import spade
import asyncio
import logging
import random
import json
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

# Create logs directory
LOGS_DIR = Path("lab4_logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging
log_filename = LOGS_DIR / f"lab4_message_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
message_log_file = LOGS_DIR / f"lab4_acl_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# FIPA-ACL PERFORMATIVES AND MESSAGE STRUCTURE

class FIPAPerformative(Enum):
    """FIPA-ACL Performatives"""
    INFORM = "inform"           # Inform about a fact
    REQUEST = "request"         # Request an action
    AGREE = "agree"            # Agree to perform action
    REFUSE = "refuse"          # Refuse to perform action
    CONFIRM = "confirm"        # Confirm truth of proposition
    QUERY_IF = "query-if"      # Query if proposition is true
    PROPOSE = "propose"        # Propose an action
    ACCEPT_PROPOSAL = "accept-proposal"
    REJECT_PROPOSAL = "reject-proposal"


class MessageType(Enum):
    """Message content types"""
    DISASTER_ALERT = "disaster_alert"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_RESPONSE = "resource_response"
    STATUS_UPDATE = "status_update"
    COORDINATION_REQUEST = "coordination_request"
    TASK_ASSIGNMENT = "task_assignment"


@dataclass
class ACLMessageLog:
    """Log entry for ACL message"""
    timestamp: str
    sender: str
    receiver: str
    performative: str
    message_type: str
    content: Dict
    conversation_id: str = None
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'sender': self.sender,
            'receiver': self.receiver,
            'performative': self.performative,
            'message_type': self.message_type,
            'content': self.content,
            'conversation_id': self.conversation_id
        }


# PART 2: COMMAND CENTER AGENT (Coordinator)

class CommandCenterAgent(Agent):
    """
    Command center that coordinates disaster response
    Receives disaster alerts and requests resources from field agents
    """
    
    class ReceiveAlertBehaviour(CyclicBehaviour):
        """Continuously listen for disaster alerts"""
        
        async def run(self):
            # Wait for INFORM messages about disasters
            msg = await self.receive(timeout=1)
            
            if msg:
                performative = msg.get_metadata("performative")
                msg_type = msg.get_metadata("message_type")
                
                # Log received message
                log_entry = ACLMessageLog(
                    timestamp=datetime.now().isoformat(),
                    sender=str(msg.sender),
                    receiver=str(self.agent.jid),
                    performative=performative,
                    message_type=msg_type,
                    content=json.loads(msg.body) if msg.body else {},
                    conversation_id=msg.get_metadata("conversation-id")
                )
                self.agent.message_log.append(log_entry)
                
                if performative == FIPAPerformative.INFORM.value and \
                   msg_type == MessageType.DISASTER_ALERT.value:
                    
                    await self._handle_disaster_alert(msg)
    
        async def _handle_disaster_alert(self, msg: Message):
            """Handle incoming disaster alert"""
            disaster_data = json.loads(msg.body)
            
            logger.warning(f"\n{'='*70}")
            logger.warning(f"[CommandCenter] 🚨 DISASTER ALERT RECEIVED")
            logger.warning(f"{'='*70}")
            logger.warning(f"From: {msg.sender}")
            logger.warning(f"Performative: INFORM")
            logger.warning(f"Event ID: {disaster_data.get('event_id')}")
            logger.warning(f"Type: {disaster_data.get('disaster_type')}")
            logger.warning(f"Severity: {disaster_data.get('severity_name')}")
            logger.warning(f"{'='*70}\n")
            
            # Request resources from rescue agents
            await self._request_rescue_resources(disaster_data)
    
        async def _request_rescue_resources(self, disaster_data: Dict):
            """Send REQUEST to rescue agents for resources"""
            logger.info(f"[CommandCenter] 📤 Requesting resources from rescue agents...")
            
            # Determine resources needed based on severity
            severity = disaster_data.get('severity', 1)
            resources_needed = {
                'rescue_teams': severity * 2,
                'medical_units': severity * 1,
                'equipment': severity * 3
            }
            
            # Send REQUEST to rescue agents
            for rescue_agent in self.agent.rescue_agents:
                msg = Message(to=rescue_agent)
                msg.set_metadata("performative", FIPAPerformative.REQUEST.value)
                msg.set_metadata("message_type", MessageType.RESOURCE_REQUEST.value)
                msg.set_metadata("conversation-id", disaster_data.get('event_id'))
                msg.body = json.dumps({
                    'event_id': disaster_data.get('event_id'),
                    'disaster_type': disaster_data.get('disaster_type'),
                    'severity': severity,
                    'resources_requested': resources_needed
                })
                
                await self.send(msg)
                
                # Log outgoing message
                log_entry = ACLMessageLog(
                    timestamp=datetime.now().isoformat(),
                    sender=str(self.agent.jid),
                    receiver=rescue_agent,
                    performative=FIPAPerformative.REQUEST.value,
                    message_type=MessageType.RESOURCE_REQUEST.value,
                    content=json.loads(msg.body),
                    conversation_id=disaster_data.get('event_id')
                )
                self.agent.message_log.append(log_entry)
                
                logger.info(f"[CommandCenter] ✉️  REQUEST sent to {rescue_agent}")
                logger.info(f"  Resources requested: {resources_needed}\n")
    
    class ReceiveResponseBehaviour(CyclicBehaviour):
        """Listen for responses from rescue agents"""
        
        async def run(self):
            # Wait for INFORM messages with resource responses
            msg = await self.receive(timeout=1)
            
            if msg:
                performative = msg.get_metadata("performative")
                msg_type = msg.get_metadata("message_type")
                
                # Log received message
                log_entry = ACLMessageLog(
                    timestamp=datetime.now().isoformat(),
                    sender=str(msg.sender),
                    receiver=str(self.agent.jid),
                    performative=performative,
                    message_type=msg_type,
                    content=json.loads(msg.body) if msg.body else {},
                    conversation_id=msg.get_metadata("conversation-id")
                )
                self.agent.message_log.append(log_entry)
                
                if performative == FIPAPerformative.INFORM.value and \
                   msg_type == MessageType.RESOURCE_RESPONSE.value:
                    
                    response_data = json.loads(msg.body)
                    
                    logger.info(f"\n[CommandCenter] 📨 RESOURCE RESPONSE RECEIVED")
                    logger.info(f"From: {msg.sender}")
                    logger.info(f"Performative: INFORM")
                    logger.info(f"Status: {response_data.get('status')}")
                    logger.info(f"Resources: {response_data.get('resources_available')}\n")
    
    async def setup(self):
        """Initialize command center"""
        logger.info(f"\n{'='*70}")
        logger.info(f"[SETUP] Initializing CommandCenterAgent: {self.jid}")
        logger.info(f"{'='*70}\n")
        
        self.message_log: List[ACLMessageLog] = []
        self.rescue_agents = [
            "rescue1@localhost",
            "rescue2@localhost"
        ]
        
        # Add behaviour to receive disaster alerts
        alert_template = Template()
        alert_template.set_metadata("performative", FIPAPerformative.INFORM.value)
        alert_template.set_metadata("message_type", MessageType.DISASTER_ALERT.value)
        self.add_behaviour(self.ReceiveAlertBehaviour(), alert_template)
        
        # Add behaviour to receive resource responses
        response_template = Template()
        response_template.set_metadata("performative", FIPAPerformative.INFORM.value)
        response_template.set_metadata("message_type", MessageType.RESOURCE_RESPONSE.value)
        self.add_behaviour(self.ReceiveResponseBehaviour(), response_template)
        
        logger.info(f"✅ CommandCenter initialized")
        logger.info(f"📡 Monitoring rescue agents: {self.rescue_agents}\n")


# ============================================================================
# PART 3: RESCUE AGENT (Field Responder)
# ============================================================================

class RescueAgent(Agent):
    """
    Field rescue agent that responds to resource requests
    """
    
    class ReceiveRequestBehaviour(CyclicBehaviour):
        """Listen for resource requests from command center"""
        
        async def run(self):
            # Wait for REQUEST messages
            msg = await self.receive(timeout=1)
            
            if msg:
                performative = msg.get_metadata("performative")
                msg_type = msg.get_metadata("message_type")
                
                # Log received message
                log_entry = ACLMessageLog(
                    timestamp=datetime.now().isoformat(),
                    sender=str(msg.sender),
                    receiver=str(self.agent.jid),
                    performative=performative,
                    message_type=msg_type,
                    content=json.loads(msg.body) if msg.body else {},
                    conversation_id=msg.get_metadata("conversation-id")
                )
                self.agent.message_log.append(log_entry)
                
                if performative == FIPAPerformative.REQUEST.value and \
                   msg_type == MessageType.RESOURCE_REQUEST.value:
                    
                    await self._handle_resource_request(msg)
    
        async def _handle_resource_request(self, msg: Message):
            """Handle resource request and respond"""
            request_data = json.loads(msg.body)
            
            logger.info(f"\n[{self.agent.name}] 📨 RESOURCE REQUEST RECEIVED")
            logger.info(f"From: {msg.sender}")
            logger.info(f"Performative: REQUEST")
            logger.info(f"Event ID: {request_data.get('event_id')}")
            logger.info(f"Resources Requested: {request_data.get('resources_requested')}\n")
            
            # Simulate resource availability check
            await asyncio.sleep(0.5)
            
            # Check available resources
            requested = request_data.get('resources_requested', {})
            available = {
                'rescue_teams': min(requested.get('rescue_teams', 0), 
                                   self.agent.available_resources['rescue_teams']),
                'medical_units': min(requested.get('medical_units', 0), 
                                    self.agent.available_resources['medical_units']),
                'equipment': min(requested.get('equipment', 0), 
                               self.agent.available_resources['equipment'])
            }
            
            # Update available resources
            for key in available:
                self.agent.available_resources[key] -= available[key]
            
            # Send INFORM response with available resources
            response = Message(to=str(msg.sender))
            response.set_metadata("performative", FIPAPerformative.INFORM.value)
            response.set_metadata("message_type", MessageType.RESOURCE_RESPONSE.value)
            response.set_metadata("conversation-id", request_data.get('event_id'))
            response.body = json.dumps({
                'event_id': request_data.get('event_id'),
                'agent_id': self.agent.name,
                'status': 'resources_allocated',
                'resources_available': available
            })
            
            await self.send(response)
            
            # Log outgoing message
            log_entry = ACLMessageLog(
                timestamp=datetime.now().isoformat(),
                sender=str(self.agent.jid),
                receiver=str(msg.sender),
                performative=FIPAPerformative.INFORM.value,
                message_type=MessageType.RESOURCE_RESPONSE.value,
                content=json.loads(response.body),
                conversation_id=request_data.get('event_id')
            )
            self.agent.message_log.append(log_entry)
            
            logger.info(f"[{self.agent.name}] ✅ INFORM response sent")
            logger.info(f"  Resources allocated: {available}")
            logger.info(f"  Remaining: {self.agent.available_resources}\n")
    
    async def setup(self):
        """Initialize rescue agent"""
        logger.info(f"[SETUP] Initializing {self.name}: {self.jid}\n")
        
        self.message_log: List[ACLMessageLog] = []
        self.available_resources = {
            'rescue_teams': random.randint(3, 8),
            'medical_units': random.randint(2, 5),
            'equipment': random.randint(5, 15)
        }
        
        logger.info(f"[{self.name}] Initial resources: {self.available_resources}")
        
        # Add behaviour to receive requests
        request_template = Template()
        request_template.set_metadata("performative", FIPAPerformative.REQUEST.value)
        request_template.set_metadata("message_type", MessageType.RESOURCE_REQUEST.value)
        self.add_behaviour(self.ReceiveRequestBehaviour(), request_template)
        
        logger.info(f"✅ {self.name} initialized and ready\n")


# ============================================================================
# PART 4: SENSOR AGENT (Event Generator)
# ============================================================================

class SensorAgent(Agent):
    """
    Sensor that detects disasters and sends INFORM messages
    """
    
    class DetectDisasterBehaviour(OneShotBehaviour):
        """Generate and send disaster alert"""
        
        async def run(self):
            await asyncio.sleep(2)  # Wait before generating alert
            
            # Generate disaster event
            disaster = self._generate_disaster()
            
            logger.warning(f"\n{'='*70}")
            logger.warning(f"[SensorAgent] 🚨 DISASTER DETECTED")
            logger.warning(f"{'='*70}")
            logger.warning(f"Event ID: {disaster['event_id']}")
            logger.warning(f"Type: {disaster['disaster_type']}")
            logger.warning(f"Severity: {disaster['severity_name']}")
            logger.warning(f"{'='*70}\n")
            
            # Send INFORM message to command center
            msg = Message(to="command@localhost")
            msg.set_metadata("performative", FIPAPerformative.INFORM.value)
            msg.set_metadata("message_type", MessageType.DISASTER_ALERT.value)
            msg.set_metadata("conversation-id", disaster['event_id'])
            msg.body = json.dumps(disaster)
            
            await self.send(msg)
            
            # Log outgoing message
            log_entry = ACLMessageLog(
                timestamp=datetime.now().isoformat(),
                sender=str(self.agent.jid),
                receiver="command@localhost",
                performative=FIPAPerformative.INFORM.value,
                message_type=MessageType.DISASTER_ALERT.value,
                content=disaster,
                conversation_id=disaster['event_id']
            )
            self.agent.message_log.append(log_entry)
            
            logger.info(f"[SensorAgent] 📤 INFORM message sent to CommandCenter\n")
        
        def _generate_disaster(self) -> Dict:
            """Generate random disaster event"""
            disaster_types = ["Earthquake", "Flood", "Fire", "Hurricane"]
            severity_levels = [
                (1, "MINIMAL"),
                (2, "LOW"),
                (3, "MODERATE"),
                (4, "HIGH"),
                (5, "CRITICAL")
            ]
            
            disaster_type = random.choice(disaster_types)
            severity, severity_name = random.choice(severity_levels)
            
            return {
                'event_id': f"EVENT-{random.randint(1000, 9999)}",
                'disaster_type': disaster_type,
                'severity': severity,
                'severity_name': severity_name,
                'location': "Disaster Zone Alpha",
                'timestamp': datetime.now().isoformat()
            }
    
    async def setup(self):
        """Initialize sensor agent"""
        logger.info(f"[SETUP] Initializing SensorAgent: {self.jid}\n")
        
        self.message_log: List[ACLMessageLog] = []
        
        # Add disaster detection behaviour
        self.add_behaviour(self.DetectDisasterBehaviour())
        
        logger.info(f"✅ SensorAgent initialized\n")


# ============================================================================
# PART 5: MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("\n" + "="*70)
    print("LAB 4: AGENT COMMUNICATION USING FIPA-ACL")
    print("Multi-Agent Coordination Protocol")
    print("="*70 + "\n")
    
    # Agent credentials
    agents_config = {
        'sensor': ('sensor@localhost', 'password123'),
        'command': ('command@localhost', 'password123'),
        'rescue1': ('rescue1@localhost', 'password123'),
        'rescue2': ('rescue2@localhost', 'password123')
    }
    
    print("🤖 Creating Agents...")
    for name, (jid, _) in agents_config.items():
        print(f"   {name.capitalize()}: {jid}")
    print(f"📁 Log Directory: {LOGS_DIR.absolute()}\n")
    
    # Create agents
    sensor = SensorAgent(*agents_config['sensor'])
    command = CommandCenterAgent(*agents_config['command'])
    rescue1 = RescueAgent(*agents_config['rescue1'])
    rescue1.agent_name = "RescueAgent1"
    rescue2 = RescueAgent(*agents_config['rescue2'])
    rescue2.agent_name = "RescueAgent2"
    
    try:
        print("🚀 Starting Agents...")
        await command.start(auto_register=True)
        await rescue1.start(auto_register=True)
        await rescue2.start(auto_register=True)
        await sensor.start(auto_register=True)
        print("✅ All agents active\n")
        
        print("⏱️  Running for 15 seconds...")
        print("💡 Watch for FIPA-ACL messages (INFORM, REQUEST)!\n")
        
        # Let agents communicate
        await asyncio.sleep(15)
        
        print("\n" + "="*70)
        print("🛑 Shutting down agents...")
        
        # Collect all messages
        all_messages = []
        all_messages.extend([m.to_dict() for m in sensor.message_log])
        all_messages.extend([m.to_dict() for m in command.message_log])
        all_messages.extend([m.to_dict() for m in rescue1.message_log])
        all_messages.extend([m.to_dict() for m in rescue2.message_log])
        
        # Export message log
        with open(message_log_file, 'w') as f:
            json.dump({
                'session_timestamp': session_timestamp,
                'total_messages': len(all_messages),
                'messages': sorted(all_messages, key=lambda x: x['timestamp'])
            }, f, indent=2)
        
        await sensor.stop()
        await command.stop()
        await rescue1.stop()
        await rescue2.stop()
        
        # Final summary
        print("\n" + "="*70)
        print("📋 LAB 4 SUMMARY")
        print("="*70)
        print(f"Total ACL Messages Exchanged: {len(all_messages)}")
        
        performative_counts = {}
        for msg in all_messages:
            perf = msg['performative']
            performative_counts[perf] = performative_counts.get(perf, 0) + 1
        
        print("\nPerformatives Used:")
        for perf, count in performative_counts.items():
            print(f"  {perf.upper()}: {count}")
        
        print("\n" + "="*70)
        print("📁 DELIVERABLES GENERATED")
        print("="*70)
        print(f"1. Message Logs (TXT): {log_filename}")
        print(f"2. ACL Messages (JSON): {message_log_file}")
        print(f"3. Communication Code: lab4_fipa_acl_communication.py")
        print("\n💡 Submit these files to your instructor!")
        
        print("\n" + "="*70)
        print("✅ Lab 4 Complete!")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure ejabberd is running")
        print("  2. Create all agent accounts:")
        for name, (jid, pwd) in agents_config.items():
            username = jid.split('@')[0]
            print(f"     sudo ejabberdctl register {username} localhost {pwd}")
        return False
    
    return True


if __name__ == "__main__":
    spade.run(main())