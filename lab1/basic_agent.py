import spade
import asyncio
import logging
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour

# Enable logging to see connection details
logging.basicConfig(level=logging.INFO)

class GreetingBehaviour(OneShotBehaviour):
    """One-time greeting behavior"""
    async def run(self):
        print(f"✓ Greeting: Hello! I am agent {self.agent.jid} and I am now active.")
        await asyncio.sleep(1)

class MonitoringBehaviour(CyclicBehaviour):
    """Periodic monitoring behavior"""
    async def run(self):
        print(f"✓ Monitoring: Agent {self.agent.jid} is running...")
        await asyncio.sleep(2)

class MyAgent(Agent):
    """Basic SPADE Agent with multiple behaviors"""
    
    async def setup(self):
        """Setup method called when agent starts"""
        print(f"\n[SETUP] Agent {self.jid} is initializing...")
        
        # Add greeting behavior
        greeting = GreetingBehaviour()
        self.add_behaviour(greeting)
        
        # Add monitoring behavior
        monitor = MonitoringBehaviour()
        self.add_behaviour(monitor)
        
        print(f"[SETUP] Agent {self.jid} setup complete!\n")
    
    async def on_stop(self):
        """Called when agent stops"""
        print(f"\n[STOP] Agent {self.jid} is stopping...")

async def main():
    """Main entry point"""
    print("="*60)
    print("SPADE Agent Framework - Basic Agent Example")
    print("="*60)
    
    # Create agent with credentials
    # Make sure these credentials are pre-registered on the XMPP server
    agent = MyAgent("testagent@localhost", "password123")
    
    try:
        print("\n[STARTING] Launching agent...")
        await agent.start(auto_register=True)
        
        print("[RUNNING] Agent is active. Running for 10 seconds...")
        await asyncio.sleep(10)
        
        print("\n[STOPPING] Shutting down agent...")
        await agent.stop()
        print("[SUCCESS] Agent stopped successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Connection error: {e}")
        print("Troubleshooting:")
        print("  1. Ensure Ejabberd XMPP server is running: sudo service ejabberd start")
        print("  2. Check server is accessible on localhost:5222")
        print("  3. Verify agent credentials are registered on the server")
        return False
    
    print("\n" + "="*60)
    return True

if __name__ == "__main__":
    # Run the agent using spade.run()
    spade.run(main())