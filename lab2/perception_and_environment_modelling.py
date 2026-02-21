#!/usr/bin/env python3
"""
LAB 2: PERCEPTION AND ENVIRONMENT MODELING (Enhanced with File Logging)
=======================================================================

Objective: Implement agent perception of environmental and disaster-related events

This enhanced version includes:
1. Simulated disaster environment with dynamic conditions
2. SensorAgent that periodically monitors environmental conditions
3. Event generation and logging to FILES for submission
4. JSON and CSV export of disaster events

Date: 2026-01-29
"""

import spade
import asyncio
import logging
import random
import json
import csv
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour

# Create logs directory
LOGS_DIR = Path("disaster_logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging to both console and file
log_filename = LOGS_DIR / f"sensor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
# PART 1: DISASTER ENVIRONMENT MODELING
# ============================================================================

class DisasterType(Enum):
    """Types of disasters that can occur"""
    EARTHQUAKE = "Earthquake"
    FLOOD = "Flood"
    FIRE = "Fire"
    HURRICANE = "Hurricane"
    TORNADO = "Tornado"
    TSUNAMI = "Tsunami"


class SeverityLevel(Enum):
    """Severity levels for disasters"""
    MINIMAL = 1      # Minor damage
    LOW = 2          # Some damage
    MODERATE = 3     # Significant damage
    HIGH = 4         # Major damage
    CRITICAL = 5     # Catastrophic damage


@dataclass
class EnvironmentalCondition:
    """Represents current environmental conditions"""
    timestamp: str
    temperature: float  # Celsius
    humidity: float     # Percentage
    wind_speed: float   # km/h
    air_quality: int    # AQI (0-500)
    water_level: float  # meters
    seismic_activity: float  # Richter scale
    
    def to_dict(self) -> Dict:
        return asdict(self)


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
    damage_cost_usd: float
    description: str
    
    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'disaster_type': self.disaster_type.value,
            'severity': self.severity.value,
            'severity_name': self.severity.name,
            'location': self.location,
            'timestamp': self.timestamp,
            'affected_area_km2': self.affected_area_km2,
            'casualties_estimated': self.casualties_estimated,
            'damage_cost_usd': self.damage_cost_usd,
            'description': self.description
        }
    
    def to_csv_row(self) -> List:
        """Convert to CSV row format"""
        return [
            self.event_id,
            self.disaster_type.value,
            self.severity.name,
            self.severity.value,
            self.location,
            self.timestamp,
            self.affected_area_km2,
            self.casualties_estimated,
            self.damage_cost_usd,
            self.description
        ]


class DisasterEnvironment:
    """
    Simulates a disaster-prone environment with dynamic conditions
    """
    
    def __init__(self, location: str = "Disaster Zone Alpha"):
        self.location = location
        self.current_conditions = self._initialize_conditions()
        self.active_disasters: List[DisasterEvent] = []
        self.event_history: List[DisasterEvent] = []
        self.event_counter = 0
        self.conditions_history: List[EnvironmentalCondition] = []
        
    def _initialize_conditions(self) -> EnvironmentalCondition:
        """Initialize with normal environmental conditions"""
        return EnvironmentalCondition(
            timestamp=datetime.now().isoformat(),
            temperature=22.0,
            humidity=60.0,
            wind_speed=15.0,
            air_quality=50,
            water_level=2.0,
            seismic_activity=0.0
        )
    
    def update_conditions(self):
        """Update environmental conditions with some randomness"""
        # Simulate natural variations
        self.current_conditions.temperature += random.uniform(-2, 2)
        self.current_conditions.humidity += random.uniform(-5, 5)
        self.current_conditions.wind_speed += random.uniform(-3, 3)
        self.current_conditions.air_quality += random.randint(-10, 10)
        self.current_conditions.water_level += random.uniform(-0.5, 0.5)
        self.current_conditions.seismic_activity = random.uniform(0, 2)
        
        # Keep values in reasonable ranges
        self.current_conditions.temperature = max(-10, min(45, self.current_conditions.temperature))
        self.current_conditions.humidity = max(0, min(100, self.current_conditions.humidity))
        self.current_conditions.wind_speed = max(0, min(150, self.current_conditions.wind_speed))
        self.current_conditions.air_quality = max(0, min(500, self.current_conditions.air_quality))
        self.current_conditions.water_level = max(0, min(20, self.current_conditions.water_level))
        
        self.current_conditions.timestamp = datetime.now().isoformat()
        
        # Store conditions history
        self.conditions_history.append(EnvironmentalCondition(**asdict(self.current_conditions)))
    
    def check_for_disasters(self) -> List[DisasterEvent]:
        """
        Check environmental conditions and potentially generate disaster events
        """
        new_disasters = []
        
        # Earthquake detection (based on seismic activity)
        if self.current_conditions.seismic_activity > 4.0:
            severity = self._determine_earthquake_severity(self.current_conditions.seismic_activity)
            event = self._create_disaster_event(DisasterType.EARTHQUAKE, severity)
            new_disasters.append(event)
        
        # Flood detection (based on water level)
        if self.current_conditions.water_level > 10.0:
            severity = self._determine_flood_severity(self.current_conditions.water_level)
            event = self._create_disaster_event(DisasterType.FLOOD, severity)
            new_disasters.append(event)
        
        # Fire detection (based on temperature and humidity)
        if self.current_conditions.temperature > 35 and self.current_conditions.humidity < 20:
            severity = self._determine_fire_severity(self.current_conditions.temperature)
            event = self._create_disaster_event(DisasterType.FIRE, severity)
            new_disasters.append(event)
        
        # Hurricane detection (based on wind speed)
        if self.current_conditions.wind_speed > 120:
            severity = self._determine_hurricane_severity(self.current_conditions.wind_speed)
            event = self._create_disaster_event(DisasterType.HURRICANE, severity)
            new_disasters.append(event)
        
        # Random disaster events (10% chance each cycle)
        if random.random() < 0.10:
            disaster_type = random.choice(list(DisasterType))
            severity = random.choice(list(SeverityLevel))
            event = self._create_disaster_event(disaster_type, severity)
            new_disasters.append(event)
        
        # Add to active disasters and history
        for event in new_disasters:
            self.active_disasters.append(event)
            self.event_history.append(event)
        
        return new_disasters
    
    def _create_disaster_event(self, disaster_type: DisasterType, severity: SeverityLevel) -> DisasterEvent:
        """Create a new disaster event"""
        self.event_counter += 1
        
        # Generate event details based on severity
        affected_area = severity.value * random.uniform(10, 50)
        casualties = severity.value * random.randint(0, 100)
        damage_cost = severity.value * random.uniform(1_000_000, 100_000_000)
        
        return DisasterEvent(
            event_id=f"EVENT-{self.event_counter:04d}",
            disaster_type=disaster_type,
            severity=severity,
            location=self.location,
            timestamp=datetime.now().isoformat(),
            affected_area_km2=round(affected_area, 2),
            casualties_estimated=casualties,
            damage_cost_usd=round(damage_cost, 2),
            description=self._generate_description(disaster_type, severity)
        )
    
    def _determine_earthquake_severity(self, magnitude: float) -> SeverityLevel:
        """Determine earthquake severity based on Richter scale"""
        if magnitude < 4.5:
            return SeverityLevel.MINIMAL
        elif magnitude < 5.5:
            return SeverityLevel.LOW
        elif magnitude < 6.5:
            return SeverityLevel.MODERATE
        elif magnitude < 7.5:
            return SeverityLevel.HIGH
        else:
            return SeverityLevel.CRITICAL
    
    def _determine_flood_severity(self, water_level: float) -> SeverityLevel:
        """Determine flood severity based on water level"""
        if water_level < 12:
            return SeverityLevel.MODERATE
        elif water_level < 15:
            return SeverityLevel.HIGH
        else:
            return SeverityLevel.CRITICAL
    
    def _determine_fire_severity(self, temperature: float) -> SeverityLevel:
        """Determine fire severity based on temperature"""
        if temperature < 38:
            return SeverityLevel.LOW
        elif temperature < 42:
            return SeverityLevel.MODERATE
        else:
            return SeverityLevel.HIGH
    
    def _determine_hurricane_severity(self, wind_speed: float) -> SeverityLevel:
        """Determine hurricane severity based on wind speed"""
        if wind_speed < 130:
            return SeverityLevel.MODERATE
        elif wind_speed < 140:
            return SeverityLevel.HIGH
        else:
            return SeverityLevel.CRITICAL
    
    def _generate_description(self, disaster_type: DisasterType, severity: SeverityLevel) -> str:
        """Generate a description for the disaster event"""
        descriptions = {
            DisasterType.EARTHQUAKE: f"{severity.name} earthquake detected with significant ground shaking",
            DisasterType.FLOOD: f"{severity.name} flooding detected with rising water levels",
            DisasterType.FIRE: f"{severity.name} wildfire detected with rapid spread",
            DisasterType.HURRICANE: f"{severity.name} hurricane detected with extreme winds",
            DisasterType.TORNADO: f"{severity.name} tornado detected with severe damage potential",
            DisasterType.TSUNAMI: f"{severity.name} tsunami warning with potential coastal impact"
        }
        return descriptions.get(disaster_type, f"{severity.name} disaster event")
    
    def get_current_state(self) -> Dict:
        """Get current environment state"""
        return {
            'location': self.location,
            'conditions': self.current_conditions.to_dict(),
            'active_disasters': len(self.active_disasters),
            'total_events': len(self.event_history)
        }
    
    def export_conditions_to_json(self, filename: Path):
        """Export conditions history to JSON file"""
        data = [cond.to_dict() for cond in self.conditions_history]
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def export_conditions_to_csv(self, filename: Path):
        """Export conditions history to CSV file"""
        if not self.conditions_history:
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Temperature(°C)', 'Humidity(%)', 'Wind Speed(km/h)', 
                           'Air Quality', 'Water Level(m)', 'Seismic Activity'])
            
            for cond in self.conditions_history:
                writer.writerow([
                    cond.timestamp,
                    cond.temperature,
                    cond.humidity,
                    cond.wind_speed,
                    cond.air_quality,
                    cond.water_level,
                    cond.seismic_activity
                ])


# ============================================================================
# PART 2: SENSOR AGENT IMPLEMENTATION
# ============================================================================

class SensorAgent(Agent):
    """
    Agent that monitors environmental conditions and detects disasters
    """
    
    class EnvironmentMonitorBehaviour(PeriodicBehaviour):
        """Periodically monitors environmental conditions"""
        
        async def on_start(self):
            """Initialize when behaviour starts"""
            logger.info(f"[{self.agent.jid}] Environment monitoring started")
            self.monitoring_count = 0
        
        async def run(self):
            """Monitor environment and detect disasters"""
            self.monitoring_count += 1
            
            # Update environmental conditions
            self.agent.environment.update_conditions()
            conditions = self.agent.environment.current_conditions
            
            # Log current conditions
            logger.info(f"\n{'='*70}")
            logger.info(f"[MONITORING #{self.monitoring_count}] Environmental Scan")
            logger.info(f"{'='*70}")
            logger.info(f"📍 Location: {self.agent.environment.location}")
            logger.info(f"🌡️  Temperature: {conditions.temperature:.1f}°C")
            logger.info(f"💧 Humidity: {conditions.humidity:.1f}%")
            logger.info(f"💨 Wind Speed: {conditions.wind_speed:.1f} km/h")
            logger.info(f"🏭 Air Quality Index: {conditions.air_quality}")
            logger.info(f"🌊 Water Level: {conditions.water_level:.1f}m")
            logger.info(f"📊 Seismic Activity: {conditions.seismic_activity:.2f}")
            
            # Check for disasters
            new_disasters = self.agent.environment.check_for_disasters()
            
            if new_disasters:
                logger.warning(f"\n🚨 DISASTER ALERT! {len(new_disasters)} new event(s) detected:")
                for event in new_disasters:
                    self._log_disaster_event(event)
                    # Store in agent's event log
                    self.agent.disaster_log.append(event)
            else:
                logger.info(f"✅ No disasters detected - Conditions normal")
            
            logger.info(f"{'='*70}\n")
        
        def _log_disaster_event(self, event: DisasterEvent):
            """Log detailed information about a disaster event"""
            logger.warning(f"\n  {'─'*66}")
            logger.warning(f"  🆔 Event ID: {event.event_id}")
            logger.warning(f"  ⚠️  Type: {event.disaster_type.value}")
            logger.warning(f"  📊 Severity: {event.severity.name} (Level {event.severity.value}/5)")
            logger.warning(f"  📍 Location: {event.location}")
            logger.warning(f"  🕐 Time: {event.timestamp}")
            logger.warning(f"  📏 Affected Area: {event.affected_area_km2} km²")
            logger.warning(f"  👥 Estimated Casualties: {event.casualties_estimated}")
            logger.warning(f"  💰 Estimated Damage: ${event.damage_cost_usd:,.2f} USD")
            logger.warning(f"  📝 Description: {event.description}")
            logger.warning(f"  {'─'*66}")
    
    class EventLoggerBehaviour(CyclicBehaviour):
        """Continuously logs and manages disaster events"""
        
        async def run(self):
            """Process and manage logged events"""
            await asyncio.sleep(5)
            
            if self.agent.disaster_log:
                # Generate statistics
                total_events = len(self.agent.disaster_log)
                severity_counts = {}
                type_counts = {}
                
                for event in self.agent.disaster_log:
                    severity_counts[event.severity.name] = severity_counts.get(event.severity.name, 0) + 1
                    type_counts[event.disaster_type.value] = type_counts.get(event.disaster_type.value, 0) + 1
                
                logger.info(f"\n{'='*70}")
                logger.info(f"📊 DISASTER STATISTICS REPORT")
                logger.info(f"{'='*70}")
                logger.info(f"Total Events Recorded: {total_events}")
                logger.info(f"\nBy Severity:")
                for severity, count in sorted(severity_counts.items()):
                    logger.info(f"  {severity}: {count}")
                logger.info(f"\nBy Type:")
                for dtype, count in sorted(type_counts.items()):
                    logger.info(f"  {dtype}: {count}")
                logger.info(f"{'='*70}\n")
    
    async def setup(self):
        """Initialize the sensor agent"""
        logger.info(f"\n{'='*70}")
        logger.info(f"[SETUP] Initializing SensorAgent: {self.jid}")
        logger.info(f"{'='*70}\n")
        
        # Initialize environment
        self.environment = DisasterEnvironment("Disaster Monitoring Zone")
        self.disaster_log = []
        
        # Add monitoring behaviour (runs every 3 seconds)
        monitor = self.EnvironmentMonitorBehaviour(period=3)
        self.add_behaviour(monitor)
        
        # Add event logger behaviour
        logger_behaviour = self.EventLoggerBehaviour()
        self.add_behaviour(logger_behaviour)
        
        logger.info(f"✅ SensorAgent initialized and ready to monitor")
        logger.info(f"📡 Monitoring location: {self.environment.location}")
        logger.info(f"⏱️  Scan interval: 3 seconds")
        logger.info(f"📁 Log file: {log_filename}\n")
    
    def export_disaster_events_json(self, filename: Path):
        """Export disaster events to JSON file"""
        data = {
            'monitoring_session': {
                'start_time': datetime.now().isoformat(),
                'location': self.environment.location,
                'total_events': len(self.disaster_log)
            },
            'events': [event.to_dict() for event in self.disaster_log]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✅ Exported {len(self.disaster_log)} events to {filename}")
    
    def export_disaster_events_csv(self, filename: Path):
        """Export disaster events to CSV file"""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Event ID', 'Disaster Type', 'Severity Name', 'Severity Level',
                           'Location', 'Timestamp', 'Affected Area (km²)', 'Casualties',
                           'Damage Cost (USD)', 'Description'])
            
            for event in self.disaster_log:
                writer.writerow(event.to_csv_row())
        
        logger.info(f"✅ Exported {len(self.disaster_log)} events to {filename}")


# ============================================================================
# PART 3: MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("\n" + "="*70)
    print("LAB 2: PERCEPTION AND ENVIRONMENT MODELING")
    print("Disaster Detection and Monitoring System")
    print("="*70 + "\n")
    
    # Agent credentials
    AGENT_JID = "sensor@localhost"
    AGENT_PASSWORD = "password123"
    
    print(f"🤖 Creating SensorAgent...")
    print(f"   JID: {AGENT_JID}")
    print(f"   Mission: Environmental monitoring and disaster detection")
    print(f"📁 Log Directory: {LOGS_DIR.absolute()}\n")
    
    # Create sensor agent
    sensor_agent = SensorAgent(AGENT_JID, AGENT_PASSWORD)
    
    try:
        print("🚀 Starting SensorAgent...")
        await sensor_agent.start(auto_register=True)
        print("✅ SensorAgent is now active and monitoring\n")
        
        print("⏱️  Running for 30 seconds...")
        print("💡 Watch for disaster alerts and environmental updates!\n")
        
        # Let the agent run and monitor
        await asyncio.sleep(30)
        
        print("\n" + "="*70)
        print("🛑 Shutting down monitoring system...")
        print("📊 Generating final reports...")
        
        # Export all data to files
        events_json = LOGS_DIR / f"disaster_events_{session_timestamp}.json"
        events_csv = LOGS_DIR / f"disaster_events_{session_timestamp}.csv"
        conditions_json = LOGS_DIR / f"environmental_conditions_{session_timestamp}.json"
        conditions_csv = LOGS_DIR / f"environmental_conditions_{session_timestamp}.csv"
        
        # Export disaster events
        sensor_agent.export_disaster_events_json(events_json)
        sensor_agent.export_disaster_events_csv(events_csv)
        
        # Export environmental conditions
        sensor_agent.environment.export_conditions_to_json(conditions_json)
        sensor_agent.environment.export_conditions_to_csv(conditions_csv)
        
        await sensor_agent.stop()
        
        # Final report
        print("\n" + "="*70)
        print("📋 FINAL DISASTER REPORT")
        print("="*70)
        print(f"Total disasters detected: {len(sensor_agent.disaster_log)}")
        
        if sensor_agent.disaster_log:
            print("\nDisaster Events Summary:")
            for i, event in enumerate(sensor_agent.disaster_log, 1):
                print(f"\n{i}. {event.disaster_type.value} - {event.severity.name}")
                print(f"   Event ID: {event.event_id}")
                print(f"   Area Affected: {event.affected_area_km2} km²")
                print(f"   Estimated Damage: ${event.damage_cost_usd:,.2f}")
        else:
            print("\n✅ No disasters occurred during monitoring period")
        
        print("\n" + "="*70)
        print("📁 GENERATED FILES (for submission)")
        print("="*70)
        print(f"1. Console & System Log: {log_filename}")
        print(f"2. Disaster Events (JSON): {events_json}")
        print(f"3. Disaster Events (CSV): {events_csv}")
        print(f"4. Environmental Data (JSON): {conditions_json}")
        print(f"5. Environmental Data (CSV): {conditions_csv}")
        print("\n💡 Submit these files to your instructor!")
        
        print("\n" + "="*70)
        print("✅ Lab 2 Complete!")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure ejabberd is running: sudo systemctl start ejabberd")
        print("  2. Check credentials: sudo ejabberdctl registered_users localhost")
        return False
    
    return True


if __name__ == "__main__":
    # Run the simulation
    spade.run(main())