"""
Pub/Sub command implementations for Redis server.
Handles SUBSCRIBE, UNSUBSCRIBE, PUBLISH, and PUBSUB commands.
"""

from .base import BaseCommandHandler
from ..response import *


class PubSubCommands(BaseCommandHandler):
    """Handler for pub/sub commands."""
    
    def __init__(self, storage, persistence_manager=None, pubsub_manager=None):
        super().__init__(storage, persistence_manager)
        self.pubsub_manager = pubsub_manager
        self.current_client = None  # Will be set by command handler
    
    def set_current_client(self, client):
        """Set the current client for command execution."""
        self.current_client = client
    
    def subscribe(self, *channels):
        """
        SUBSCRIBE channel [channel ...]
        Subscribe to one or more channels.
        """
        if not channels:
            return error("Wrong number of arguments for 'subscribe' command")
        
        if not self.current_client:
            return error("No client context available")
        
        if not self.pubsub_manager:
            return error("Pub/Sub not available")

        # Subscribe to channels
        results = self.pubsub_manager.subscribe(self.current_client, *channels)
        
        # Format response as array of subscription confirmations
        responses = []
        for channel, subscription_count in results:
            # Each subscription confirmation: ["subscribe", channel, subscription_count]
            confirmation = [
                bulk_string("subscribe"),
                bulk_string(channel),
                integer(subscription_count)
            ]
            responses.append(array(confirmation))
        
        # Return all confirmations
        return b"".join(responses)
    
    def unsubscribe(self, *channels):
        """
        UNSUBSCRIBE [channel [channel ...]]
        Unsubscribe from channels. If no channels specified, unsubscribe from all.
        """
        if not self.current_client:
            return error("no client context available")
        
        if not self.pubsub_manager:
            return error("pub/sub not available")
        
        # Unsubscribe from channels
        results = self.pubsub_manager.unsubscribe(self.current_client, *channels)
        
        # If no channels were specified and client had no subscriptions
        if not results:
            # Return single unsubscribe confirmation with None channel
            confirmation = [
                bulk_string("unsubscribe"),
                null_bulk_string(),
                integer(0)
            ]
            return array(confirmation)
        
        # Format response as array of unsubscription confirmations
        responses = []
        for channel, subscription_count in results:
            # Each unsubscription confirmation: ["unsubscribe", channel, subscription_count]
            confirmation = [
                bulk_string("unsubscribe"),
                bulk_string(channel),
                integer(subscription_count)
            ]
            responses.append(array(confirmation))
        
        return b"".join(responses)
    
    def publish(self, channel, *message_parts):
        """
        PUBLISH channel message
        Publish a message to a channel.
        Returns the number of clients that received the message.
        """
        if not channel or not message_parts:
            return error("wrong number of arguments for 'publish' command")
        
        if not self.pubsub_manager:
            return error("pub/sub not available")
        
        # Join all message parts to handle multi-word messages
        message = " ".join(message_parts)
        
        # Remove surrounding quotes if present
        if len(message) >= 2 and message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        elif len(message) >= 2 and message.startswith("'") and message.endswith("'"):
            message = message[1:-1]
        
        # Publish message and get subscriber count
        subscriber_count = self.pubsub_manager.publish(channel, message)
        
        return integer(subscriber_count)
    
    def pubsub(self, subcommand, *args):
        """
        PUBSUB subcommand [argument [argument ...]]
        Introspection commands for the pub/sub subsystem.
        """
        if not self.pubsub_manager:
            return error("pub/sub not available")
        
        subcommand = subcommand.upper()
        
        if subcommand == "CHANNELS":
            # PUBSUB CHANNELS [pattern]
            pattern = args[0] if args else None
            channels = self.pubsub_manager.get_channels(pattern)
            
            # Return array of channel names
            channel_responses = [bulk_string(channel) for channel in channels]
            return array(channel_responses)
        
        elif subcommand == "NUMSUB":
            # PUBSUB NUMSUB [channel [channel ...]]
            if not args:
                return array([])
            
            # Return array of [channel, subscriber_count] pairs
            responses = []
            for channel in args:
                responses.append(bulk_string(channel))
                responses.append(integer(self.pubsub_manager.get_channel_subscribers(channel)))
            
            return array(responses)
        
        elif subcommand == "NUMPAT":
            # PUBSUB NUMPAT (number of pattern subscriptions)
            # For now, return 0 as we haven't implemented pattern subscriptions
            return integer(0)
        
        else:
            return error(f"unknown pubsub subcommand '{subcommand}'")
    
    def _is_write_command(self, command):
        """Override to include PUBLISH as a write command for logging."""
        pub_sub_write_commands = {'PUBLISH'}
        return (super()._is_write_command(command) or 
                command.upper() in pub_sub_write_commands)
