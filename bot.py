import os
import asyncio
from telethon import TelegramClient, events, errors, Button

# === Heroku ENV Vars ===
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

# === Runtime Vars ===
destination_chat = None
destination_topic = None
source_chat = None
source_topic = None  # New: To store the source topic ID
filter_settings = {
    "video": False,
    "pdf": False,
    "text": False,
    "image": False,
    "audio": False,
    "document": False  # For other documents besides PDF
}
authorized_users = {OWNER_ID}
stop_forwarding = False
live_forwarding = False

# === Telethon Client ===
bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- Live Forwarding Handler ---
@bot.on(events.NewMessage)
async def live_forward_handler(event):
    global live_forwarding, source_chat, source_topic, destination_chat, destination_topic, filter_settings
    
    # Check if live forwarding is active and if the message is from the designated source chat
    if not live_forwarding or event.chat_id != source_chat:
        return

    # If a source topic is set, ensure the message is from that topic
    # For live forwarding, event.reply_to_msg_id is the topic ID if it's a message within a topic
    # If it's a message in the main chat of a group/channel with topics, reply_to_msg_id might be None
    # We need to check if the message is actually in the specified topic.
    # Telethon's event.message.peer_id.channel_id or event.message.peer_id.chat_id might be useful,
    # but for topics, the message itself has a reply_to_msg_id pointing to the topic's "main" message.
    # A more robust check for topics might involve checking event.message.peer_id.topic_id if available,
    # or ensuring event.reply_to_msg_id matches the source_topic for messages *within* a topic.
    # For simplicity, sticking to reply_to_msg_id for now, assuming messages in topics reply to the topic's "root" message.
    if source_topic is not None:
        # If source_topic is set, we only forward messages that are replies to that topic's root message.
        # This is a common way to identify messages within a specific topic.
        if event.reply_to_msg_id != source_topic:
            return
    elif event.reply_to_msg_id is not None:
        # If source_topic is NOT set, but the message IS a reply to something (i.e., it's in a topic),
        # then we should NOT forward it, as we're configured for the main chat.
        return


    try:
        sent = False
        reply_to = destination_topic if destination_topic else None
        
        # Apply filters
        if filter_settings["video"] and event.video:
            await bot.send_message(destination_chat, event.message, reply_to=reply_to)
            sent = True
        elif filter_settings["pdf"] and event.document and event.document.mime_type == "application/pdf":
            await bot.send_message(destination_chat, event.message, reply_to=reply_to)
            sent = True
        elif filter_settings["text"] and event.message and not event.media:
            await bot.send_message(destination_chat, event.message, reply_to=reply_to)
            sent = True
        elif filter_settings["image"] and event.photo:
            await bot.send_message(destination_chat, event.message, reply_to=reply_to)
            sent = True
        elif filter_settings["audio"] and event.audio:
            await bot.send_message(destination_chat, event.message, reply_to=reply_to)
            sent = True
        elif filter_settings["document"] and event.document and event.document.mime_type != "application/pdf":
            await bot.send_message(destination_chat, event.message, reply_to=reply_to)
            sent = True

        if sent:
            print(f"🚀 Live forwarded message ID: {event.id} from {source_chat}/{source_topic if source_topic else 'No Topic'} to {destination_chat}/{destination_topic if destination_topic else 'No Topic'}")
    except Exception as e:
        print(f"⚠️ Error in live forwarding: {e}")

# --- /start ---
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(event):
    await event.reply(
        "🌟 Hey there, adventurer! Welcome to the Ultimate Forward Bot! 🤖💥\n"
        "I'm your high-tech messenger, ready to zip messages, videos, PDFs, and more across chats with flair! 🚀\n"
        "If you're on the VIP list, hit /help for the command arsenal. Let's launch this forwarding frenzy! 📤🔥"
    )

# --- /help ---
@bot.on(events.NewMessage(pattern=r"^/help$"))
async def help_command(event):
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not in the elite squad. 😎")
    
    help_text = (
        "🛠️ **Command Center Unlocked:** Here's your toolkit! 🔧\n\n"
        "/setdestination <chat_id>[/<topic_id>] - Lock in the target zone! For channels without topics, omit /<topic_id>. 🎯\n"
        "/addsource <source_chat_id>[/<topic_id>] - Pinpoint the origin point! For groups without topics, omit /<topic_id>. 📡\n" # Updated help text
        "/setting - Customize your forwarding filters like a pro! ⚙️\n"
        "/forward <start>-<end> - Blast messages from ID to ID! 💣\n"
        "/stop - Hit the brakes on forwarding! 🛑\n"
        "/startlive - Activate real-time forwarding magic! ✨\n"
        "/stoplive - Deactivate live mode! ❄️\n"
        "/status - Check the bot's vitals and settings! 📊\n"
        "/adduser <user_id> - Grant access to a new ally (owner only)! 🛡️\n"
        "/removeuser <user_id> - Revoke access from a user (owner only)! ⚔️\n"
        "/listusers - View the authorized squad (owner only)! 👥"
    )
    await event.reply(help_text)

# --- /adduser user_id ---
@bot.on(events.NewMessage(pattern=r"^/adduser (\d+)$"))
async def add_user(event):
    if event.sender_id != OWNER_ID:
        return await event.reply("🚫 Only the supreme commander can recruit! 👑")
    
    user_id = int(event.pattern_match.group(1))
    authorized_users.add(user_id)
    await event.reply(f"🛡️ New ally recruited! User `{user_id}` joins the ranks! 🎉🔥")

# --- /removeuser user_id ---
@bot.on(events.NewMessage(pattern=r"^/removeuser (\d+)$"))
async def remove_user(event):
    if event.sender_id != OWNER_ID:
        return await event.reply("🚫 Only the supreme commander can exile! 👑")
    
    user_id = int(event.pattern_match.group(1))
    if user_id == OWNER_ID:
        return await event.reply("⚠️ Can't exile the king! That's mutiny! 🏰")
    
    authorized_users.discard(user_id)
    await event.reply(f"⚔️ User `{user_id}` has been banished from the realm! ❌💥")

# --- /listusers ---
@bot.on(events.NewMessage(pattern=r"^/listusers$"))
async def list_users(event):
    if event.sender_id != OWNER_ID:
        return await event.reply("🚫 Only the supreme commander can view the roster! 👑")
    
    users_list = "\n".join([f"👤 {user}" for user in authorized_users])
    await event.reply(f"👥 **Authorized Squad:**\n{users_list}\nTotal operatives: {len(authorized_users)} 🚀")

# --- /setdestination chat_id[/topic_id] ---
@bot.on(events.NewMessage(pattern=r"^/setdestination (\-?\d+)(/(\d+))?$"))
async def set_destination(event):
    global destination_chat, destination_topic
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    destination_chat = int(event.pattern_match.group(1))
    topic_str = event.pattern_match.group(3)
    destination_topic = int(topic_str) if topic_str else None
    topic_info = f"Topic ID: `{destination_topic}`" if destination_topic else "No topic (channel mode)"
    await event.reply(
        f"🎯 Target acquired! Destination locked and loaded:\n"
        f"Chat ID: `{destination_chat}`\n{topic_info} 💥🚀"
    )

# --- /addsource source_chat_id[/topic_id] ---
@bot.on(events.NewMessage(pattern=r"^/addsource (\-?\d+)(/(\d+))?$")) # Updated regex to capture optional topic ID
async def add_source(event):
    global source_chat, source_topic
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    source_chat = int(event.pattern_match.group(1))
    topic_str = event.pattern_match.group(3) # Capture the topic ID part
    source_topic = int(topic_str) if topic_str else None # Set source_topic if provided

    source_info = f"Chat ID: `{source_chat}`"
    if source_topic:
        source_info += f"\nTopic ID: `{source_topic}`"
    else:
        source_info += "\nNo topic (entire chat)"

    await event.reply(f"📡 Source signal strong! Tuned into:\n{source_info}! 🔍🌐")

# --- /setting ---
@bot.on(events.NewMessage(pattern=r"^/setting$"))
async def setting_menu(event):
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    await event.reply(
        "⚙️ **Filter Forge:** Forge your forwarding filters! 🛠️🔥",
        buttons=[
            [Button.inline(f"Videos {'✅' if filter_settings['video'] else '❌'}", b"video"),
             Button.inline(f"PDFs {'✅' if filter_settings['pdf'] else '❌'}", b"pdf")],
            [Button.inline(f"Text {'✅' if filter_settings['text'] else '❌'}", b"text"),
             Button.inline(f"Images {'✅' if filter_settings['image'] else '❌'}", b"image")],
            [Button.inline(f"Audio {'✅' if filter_settings['audio'] else '❌'}", b"audio"),
             Button.inline(f"Docs {'✅' if filter_settings['document'] else '❌'}", b"document")],
        ]
    )

# --- Button Toggle ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    global filter_settings
    if event.sender_id not in authorized_users:
        return await event.answer("🚫 Access denied! You're not cleared for this op. 😎", alert=True)
    
    data = event.data.decode("utf-8")
    if data in filter_settings:
        filter_settings[data] = not filter_settings[data]
    
    await event.edit(
        "⚙️ **Filter Forge:** Forge your forwarding filters! 🛠️🔥",
        buttons=[
            [Button.inline(f"Videos {'✅' if filter_settings['video'] else '❌'}", b"video"),
             Button.inline(f"PDFs {'✅' if filter_settings['pdf'] else '❌'}", b"pdf")],
            [Button.inline(f"Text {'✅' if filter_settings['text'] else '❌'}", b"text"),
             Button.inline(f"Images {'✅' if filter_settings['image'] else '❌'}", b"image")],
            [Button.inline(f"Audio {'✅' if filter_settings['audio'] else '❌'}", b"audio"),
             Button.inline(f"Docs {'✅' if filter_settings['document'] else '❌'}", b"document")],
        ]
    )

# --- /status ---
@bot.on(events.NewMessage(pattern=r"^/status$"))
async def status_command(event):
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    filters_str = ", ".join([f"{k.capitalize()}: {'✅' if v else '❌'}" for k, v in filter_settings.items()])
    
    source_info_str = f"{source_chat}"
    if source_topic:
        source_info_str += f" (Topic: {source_topic})"
    else:
        source_info_str += " (Entire Chat)"

    destination_info_str = f"{destination_chat}"
    if destination_topic:
        destination_info_str += f" (Topic: {destination_topic})"
    else:
        destination_info_str += " (Entire Chat)"

    status_text = (
        f"📊 **Bot Status Report:**\n\n"
        f"Source: {source_info_str if source_chat else 'Not set'} 📡\n"
        f"Destination: {destination_info_str if destination_chat else 'Not set'} 🎯\n"
        f"Live Forwarding: {'Active ✨' if live_forwarding else 'Inactive ❄️'}\n"
        f"Filters: {filters_str} ⚙️\n"
        f"Authorized Users: {len(authorized_users)} 👥\n"
        f"Forwarding Active: {'Yes 🚀' if not stop_forwarding else 'No 🛑'}"
    )
    await event.reply(status_text)

# --- /startlive ---
@bot.on(events.NewMessage(pattern=r"^/startlive$"))
async def start_live(event):
    global live_forwarding
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    if not destination_chat or not source_chat:
        return await event.reply("⚠️ Setup incomplete! Set source and destination first! 🚨")
    
    live_forwarding = True
    await event.reply("✨ Live forwarding activated! Real-time magic incoming! 🔮🚀")

# --- /stoplive ---
@bot.on(events.NewMessage(pattern=r"^/stoplive$"))
async def stop_live(event):
    global live_forwarding
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    live_forwarding = False
    await event.reply("❄️ Live forwarding deactivated! Back to stealth mode. 🕶️")

# --- /stop ---
@bot.on(events.NewMessage(pattern=r"^/stop$"))
async def stop_forward(event):
    global stop_forwarding
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    stop_forwarding = True
    await event.reply("🛑 Emergency stop engaged! Halting operations... 💥")

# --- /forward start-end ---
@bot.on(events.NewMessage(pattern=r"^/forward (\d+)-(\d+)$"))
async def forward_messages(event):
    global stop_forwarding
    if event.sender_id not in authorized_users:
        return await event.reply("🚫 Access denied! You're not cleared for this op. 😎")
    
    if not destination_chat or not source_chat:
        return await event.reply("⚠️ Setup incomplete! Set source and destination first! 🚨")
    
    start_id, end_id = map(int, event.pattern_match.groups())
    if start_id > end_id:
        return await event.reply("⚠️ Invalid range! Start ID can't exceed End ID! ❌💢")
    
    total_messages = end_id - start_id + 1
    filters_str = ", ".join([k.capitalize() for k, v in filter_settings.items() if v])
    await event.reply(
        f"💣 Launching forward mission from `{start_id}` to `{end_id}`!\n"
        f"Filters engaged: {filters_str if filters_str else 'None'} ⚙️🔥"
    )
    
    # Send initial progress message
    progress_message = await event.reply("📈 Progress: 0% [▱▱▱▱▱▱▱▱▱▱] | Forwarded: 0")
    
    stop_forwarding = False
    count = 0
    processed = 0
    progress_interval = max(1, total_messages // 100)  # Update roughly every 1% or at least every message if small range
    
    # New: Flag to track if the first message has been pinned
    first_message_pinned = False

    for msg_id in range(start_id, end_id + 1):
        if stop_forwarding:
            percentage = (processed / total_messages) * 100
            filled = int(percentage / 10)
            bar = '▰' * filled + '▱' * (10 - filled)
            await progress_message.edit(f"🛑 Mission aborted! Progress: {percentage:.1f}% [{bar}] | Forwarded: {count} out of {processed} processed")
            break
        
        try:
            msg = await bot.get_messages(source_chat, ids=msg_id)
            processed += 1
            if not msg:
                # Update progress if interval met, even if message doesn't exist
                if processed % progress_interval == 0 or processed == total_messages:
                    percentage = (processed / total_messages) * 100
                    filled = int(percentage / 10)
                    bar = '▰' * filled + '▱' * (10 - filled)
                    await progress_message.edit(f"📈 Progress: {percentage:.1f}% [{bar}] | Forwarded: {count} out of {processed} processed")
                continue
            
            # New: Check if message is from the specified source topic
            if source_topic is not None and msg.reply_to_msg_id != source_topic:
                continue # Skip messages not from the source topic

            # Apply filters
            sent = False
            reply_to = destination_topic if destination_topic else None
            
            # Store the sent message object to pin it later
            sent_message_obj = None

            if filter_settings["video"] and msg.video:
                sent_message_obj = await bot.send_message(destination_chat, msg, reply_to=reply_to)
                sent = True
            elif filter_settings["pdf"] and msg.document and msg.document.mime_type == "application/pdf":
                sent_message_obj = await bot.send_message(destination_chat, msg, reply_to=reply_to)
                sent = True
            elif filter_settings["text"] and msg.message and not msg.media:
                sent_message_obj = await bot.send_message(destination_chat, msg.message, reply_to=reply_to)
                sent = True
            elif filter_settings["image"] and msg.photo:
                sent_message_obj = await bot.send_message(destination_chat, msg, reply_to=reply_to)
                sent = True
            elif filter_settings["audio"] and msg.audio:
                sent_message_obj = await bot.send_message(destination_chat, msg, reply_to=reply_to)
                sent = True
            elif filter_settings["document"] and msg.document and msg.document.mime_type != "application/pdf":
                sent_message_obj = await bot.send_message(destination_chat, msg, reply_to=reply_to)
                sent = True
            
            if sent:
                count += 1
                # New: Pin the first successfully forwarded message
                if not first_message_pinned and sent_message_obj:
                    try:
                        # Removed pin_for_everyone=True for compatibility with older Telethon versions
                        await bot.pin_message(destination_chat, sent_message_obj.id) 
                        first_message_pinned = True
                        print(f"📌 Pinned the first forwarded message (ID: {sent_message_obj.id}) in {destination_chat}")
                    except Exception as pin_e:
                        print(f"⚠️ Error pinning message {sent_message_obj.id}: {pin_e}")
            
            # Update progress
            if processed % progress_interval == 0 or processed == total_messages:
                percentage = (processed / total_messages) * 100
                filled = int(percentage / 10)
                bar = '▰' * filled + '▱' * (10 - filled)
                await progress_message.edit(f"📈 Progress: {percentage:.1f}% [{bar}] | Forwarded: {count} out of {processed} processed")
            
            await asyncio.sleep(1.5)  # Flood control
            
        except errors.FloodWaitError as e:
            wait_time = e.seconds + 2
            await event.reply(f"⏳ Flood alert! Cooling jets for {wait_time} seconds... ❄️🔥")
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"⚠️ Error forwarding message {msg_id}: {e}")
            processed += 1  # Still count as processed
            # Update progress on error if interval met
            if processed % progress_interval == 0 or processed == total_messages:
                percentage = (processed / total_messages) * 100
                filled = int(percentage / 10)
                bar = '▰' * filled + '▱' * (10 - filled)
                await progress_message.edit(f"📈 Progress: {percentage:.1f}% [{bar}] | Forwarded: {count} out of {processed} processed")
            continue
    
    if not stop_forwarding:
        await progress_message.edit(f"🏆 Mission accomplished! Progress: 100% [▰▰▰▰▰▰▰▰▰▰] | Forwarded: {count} out of {processed} processed 🎊🔥")

print("🚀 Bot ignited and ready for action! 🤖💥")
bot.run_until_disconnected()
