import os
from dotenv import load_dotenv
import google.generativeai as genai
import telegram
import json
import re
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time
import pytz

# Conversation states
ASK_AGE, ASK_WEIGHT, ASK_HEIGHT = range(3)

# Store user profiles in memory (user_id -> profile dict)
user_profiles = {}

# Global bot instance for scheduled tasks
bot_instance = None

# Simple file-based persistence for user profiles
PROFILES_FILE = "user_profiles.json"


def load_api_key():
    """Load Gemini API key from environment variables"""
    load_dotenv()
    gemini_key = os.getenv('Gemini_API_KEY')
    if not gemini_key:
        raise ValueError("Gemini_API_KEY not found in environment variables")
    return gemini_key





def load_profiles_from_disk():
    """Load user profiles from disk into memory"""
    global user_profiles
    if not os.path.exists(PROFILES_FILE):
        print(f"⚠️  Profile file not found: {PROFILES_FILE}")
        try:
            # Create an empty profiles file to avoid missing-file errors
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                f.write("{}")
            print(f"   Created empty profile file at: {os.path.abspath(PROFILES_FILE)}")
        except Exception as e:
            print(f"   Could not create profiles file: {e}")
        return
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if data:
                loaded_data = json.loads(data)
                # 🔧 FIX: Convert string keys back to integers (Telegram user IDs are integers)
                user_profiles = {int(k): v for k, v in loaded_data.items()}
                print(f"✅ Loaded {len(user_profiles)} profile(s) from disk")
                # Debug: show loaded user IDs
               # for user_id in user_profiles.keys():
                #    print(f"   - User ID: {user_id} (type: {type(user_id).__name__})")
            else:
                print(f"⚠️  Profile file is empty")
    except Exception as e:
        import traceback
        print(f"⚠️  Could not load profiles from disk: {e}")
        print(f"   Details: {traceback.format_exc()}")

def save_profiles_to_disk():
    """Persist user profiles to disk"""
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            # JSON will convert integer keys to strings, but we'll convert back on load
            f.write(json.dumps(user_profiles, indent=2))
        print(f"💾 Saved {len(user_profiles)} profile(s) to disk")
        print(f"   File location: {os.path.abspath(PROFILES_FILE)}")
        # Debug: show saved user IDs
        for user_id in user_profiles.keys():
            print(f"   - User ID: {user_id} (type: {type(user_id).__name__})")
    except Exception as e:
        import traceback
        print(f"⚠️  Could not save profiles to disk: {e}")
        print(f"   Details: {traceback.format_exc()}")

def calculate_macro_targets(age, weight_kg, height_cm):
    """
    Calculate daily macro targets based on user profile.
    Uses Mifflin-St Jeor equation for BMR and estimates TDEE.
    """
    # Calculate BMR using Mifflin-St Jeor equation
    # Assuming sedentary activity level (BMR * 1.2)
    # For simplicity, using average values - can be refined with gender/activity level
    
    # BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age + 5 (for men)
    # Using average multiplier for general population
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    tdee = bmr * 1.2  # Sedentary activity level
    
    # Macro distribution (balanced diet):
    # Protein: 20-25% of calories (1g = 4 cal)
    # Carbs: 45-50% of calories (1g = 4 cal)
    # Fats: 25-30% of calories (1g = 9 cal)
    
    protein_cal = tdee * 0.225  # 22.5%
    carbs_cal = tdee * 0.475    # 47.5%
    fats_cal = tdee * 0.30       # 30%
    
    protein_g = round(protein_cal / 4)
    carbs_g = round(carbs_cal / 4)
    fats_g = round(fats_cal / 9)
    fibre_g = round(weight_kg * 0.5)  # Rough estimate: 0.5g per kg body weight
    
    return {
        'calories': round(tdee),
        'protein': protein_g,
        'carbs': carbs_g,
        'fats': fats_g,
        'fibre': fibre_g
    }


def generate_meal_plan(gemini_key, user_profile):
    """
    Generate an Indian-style daily meal plan (breakfast, lunch, dinner)
    with quantities and macros for each meal, tailored to user's profile.
    """
    try:
        age = user_profile['age']
        weight = user_profile['weight']
        height = user_profile['height']
        macros = user_profile['macros']

        system_msg = {
            "role": "system",
            "content": "You are a nutrition-focused Indian meal planner. Provide clear, practical one-day meal plans (breakfast, lunch, dinner) with quantities and macros. Prefer simple home-cooked Indian dishes."
        }

        user_prompt = f"User Profile:\n- Age: {age} years\n- Weight: {weight} kg\n- Height: {height} cm\n\nDaily Macro Targets:\n- Calories: {macros['calories']} kcal\n- Protein: {macros['protein']} g\n- Carbohydrates: {macros['carbs']} g\n- Fats: {macros['fats']} g\n- Fibre: {macros['fibre']} g\n\nGoal: Plan meals for ONE day (breakfast, lunch, dinner). For each meal, provide dish name(s), approximate quantity for one adult, and rough macros per meal. Distribute macros across meals: breakfast ~25%, lunch ~40%, dinner ~35%. Avoid exotic ingredients and keep it practical."

        try:
            # Configure Gemini
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-3-flash-preview')

            prompt = f"""
You are a nutrition-focused Indian meal planner.

User Profile:
- Age: {age} years
- Weight: {weight} kg
- Height: {height} cm

Daily Macro Targets:
- Calories: {macros['calories']} kcal
- Protein: {macros['protein']} g
- Carbohydrates: {macros['carbs']} g
- Fats: {macros['fats']} g
- Fibre: {macros['fibre']} g

Goal:
- Plan meals for ONE day: breakfast, lunch, and dinner.
- Use Indian-style dishes that are commonly cooked at home.
- Ensure that across all 3 meals combined, the macros are close to the targets above.
- Distribute macros across meals (breakfast ~25%, lunch ~40%, dinner ~35% of daily totals).
- For EACH meal, provide:
  * Dish name(s) - be specific (e.g., "Dal Tadka with Jeera Rice" not just "Dal Rice")
  * Approximate quantity for ONE adult (in household units like cups, pieces, rotis, bowls, etc.)
  * Rough macros per meal: Protein (g), Carbs (g), Fats (g), Fibre (g), Calories (kcal)

Constraints:
- Avoid exotic ingredients that are hard to find in India.
- Prefer simple home-cooked dishes (e.g., poha, upma, dal, sabzi, roti, rice, curd, egg bhurji, paneer dishes, etc.).
- Make sure meals are practical and can be cooked at home.
- Ensure balanced nutrition across all meals.

Format your answer in a clear, easy-to-read style:

🍳 BREAKFAST
Dish: [dish name]
Quantity: [amount]
Macros: Protein: X g | Carbs: Y g | Fats: Z g | Fibre: W g | Calories: C kcal

🍽️ LUNCH
Dish: [dish name]
Quantity: [amount]
Macros: Protein: X g | Carbs: Y g | Fats: Z g | Fibre: W g | Calories: C kcal

🌙 DINNER
Dish: [dish name]
Quantity: [amount]
Macros: Protein: X g | Carbs: Y g | Fats: Z g | Fibre: W g | Calories: C kcal

📊 DAILY TOTALS
Protein: X g | Carbs: Y g | Fats: Z g | Fibre: W g | Calories: C kcal

At the end, add a brief note about how well this plan matches the user's nutritional needs.
"""

            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower():
                fallback = "Meal plan generation unavailable right now (Gemini quota exceeded). Please try again later."
                print(fallback)
                return fallback
            print(f"Error during meal plan generation: {err_msg}")
            return "Sorry, I could not generate a meal plan right now. Please try again later."
    except Exception as e:
        print(f"Error during meal plan generation: {e}")
        return "Sorry, I could not generate a meal plan right now. Please try again later."


def handle_start(update, context):
    """Handle /start command in Telegram"""
    user_id = update.message.from_user.id
    
    # Check if user already has a profile
    if user_id in user_profiles:
        # User has profile, offer to generate plan or update profile
        profile = user_profiles[user_id]
        message = (
            f"👋 Welcome back!\n\n"
            f"Your Profile:\n"
            f"Age: {profile['age']} years\n"
            f"Weight: {profile['weight']} kg\n"
            f"Height: {profile['height']} cm\n\n"
            f"Send /plan to generate your meal plan, or /profile to update your profile."
        )
        update.message.reply_text(message)
        return ConversationHandler.END
    else:
        # First time user - collect profile
        message = (
            "👋 Welcome to the Indian Meal Planner Bot!\n\n"
            "I'll help you create a personalized meal plan based on your profile.\n\n"
            "Let's start! Please tell me your age (in years):"
        )
        update.message.reply_text(message)
        return ASK_AGE


def handle_age(update, context):
    """Handle age input"""
    try:
        age = int(update.message.text.strip())
        if age < 10 or age > 120:
            update.message.reply_text("Please enter a valid age between 10 and 120 years.")
            return ASK_AGE
        
        # Store age in user_data
        user_id = update.message.from_user.id
        if user_id not in user_profiles:
            user_profiles[user_id] = {}
        user_profiles[user_id]['age'] = age
        save_profiles_to_disk()
        
        update.message.reply_text("Great! Now please tell me your weight in kg (e.g., 70):")
        return ASK_WEIGHT
    except ValueError:
        update.message.reply_text("Please enter a valid number for your age (e.g., 25):")
        return ASK_AGE


def handle_weight(update, context):
    """Handle weight input"""
    try:
        weight = float(update.message.text.strip())
        if weight < 20 or weight > 300:
            update.message.reply_text("Please enter a valid weight between 20 and 300 kg.")
            return ASK_WEIGHT
        
        # Store weight
        user_id = update.message.from_user.id
        user_profiles[user_id]['weight'] = weight
        save_profiles_to_disk()
        
        update.message.reply_text("Perfect! Now please tell me your height in cm (e.g., 170):")
        return ASK_HEIGHT
    except ValueError:
        update.message.reply_text("Please enter a valid number for your weight (e.g., 70 or 70.5):")
        return ASK_WEIGHT


def handle_height(update, context):
    """Handle height input and generate meal plan"""
    try:
        height = float(update.message.text.strip())
        if height < 100 or height > 250:
            update.message.reply_text("Please enter a valid height between 100 and 250 cm.")
            return ASK_HEIGHT
        
        # Store height and calculate macros
        user_id = update.message.from_user.id
        user_profiles[user_id]['height'] = height
        
        profile = user_profiles[user_id]
        macros = calculate_macro_targets(
            profile['age'],
            profile['weight'],
            profile['height']
        )
        user_profiles[user_id]['macros'] = macros
        save_profiles_to_disk()
        
        # Confirm profile saved
        update.message.reply_text(
            f"✅ Profile saved!\n\n"
            f"Your Daily Macro Targets:\n"
            f"Calories: {macros['calories']} kcal\n"
            f"Protein: {macros['protein']} g\n"
            f"Carbs: {macros['carbs']} g\n"
            f"Fats: {macros['fats']} g\n"
            f"Fibre: {macros['fibre']} g\n\n"
            f"Generating your personalized meal plan... Please wait ⏳"
        )
        
        # Generate meal plan
        try:
            gemini_key = load_api_key()
            plan = generate_meal_plan(gemini_key, user_profiles[user_id])
            
            # Split message if too long (Telegram limit is 4096 characters)
            if len(plan) > 4096:
                chunks = [plan[i:i+4096] for i in range(0, len(plan), 4096)]
                for chunk in chunks:
                    update.message.reply_text(chunk)
            else:
                update.message.reply_text(plan)
            
            update.message.reply_text("\n💡 Send /plan anytime to generate a new meal plan!")
            
        except Exception as e:
            update.message.reply_text(f"Error generating meal plan: {str(e)}")
        
        return ConversationHandler.END
        
    except ValueError:
        update.message.reply_text("Please enter a valid number for your height (e.g., 170 or 170.5):")
        return ASK_HEIGHT


def handle_plan(update, context):
    """Handle /plan command to generate meal plan"""
    user_id = update.message.from_user.id
    
    if user_id not in user_profiles:
        update.message.reply_text(
            "You don't have a profile yet. Please send /start to create your profile first."
        )
        return ConversationHandler.END
    
    try:
        gemini_key = load_api_key()
        update.message.reply_text("Generating your personalized meal plan... Please wait ⏳")
        
        plan = generate_meal_plan(gemini_key, user_profiles[user_id])
        
        # Split message if too long
        if len(plan) > 4096:
            chunks = [plan[i:i+4096] for i in range(0, len(plan), 4096)]
            for chunk in chunks:
                update.message.reply_text(chunk)
        else:
            update.message.reply_text(plan)
        
        update.message.reply_text("\n💡 Send /plan anytime to generate a new meal plan!")
        
    except Exception as e:
        update.message.reply_text(f"Error generating meal plan: {str(e)}")
    
    return ConversationHandler.END


def handle_test_schedule(update, context):
    """Handle /test_schedule command to manually trigger scheduled meal plans (for testing)"""
    user_id = update.message.from_user.id
    
    # Only allow this for debugging - you can remove this check in production
    update.message.reply_text("🧪 Testing scheduled meal plan delivery...")
    
    # Manually trigger the scheduled function
    try:
        send_daily_meal_plans()
        update.message.reply_text("✅ Test completed! Check console logs for details.")
    except Exception as e:
        update.message.reply_text(f"❌ Test failed: {str(e)}")
        print(f"Test schedule error: {str(e)}")
    
    return ConversationHandler.END


def handle_profile(update, context):
    """Handle /profile command to update profile"""
    user_id = update.message.from_user.id
    
    # Delete existing profile and start fresh
    if user_id in user_profiles:
        del user_profiles[user_id]
        save_profiles_to_disk()
    
    message = (
        "Let's update your profile!\n\n"
        "Please tell me your age (in years):"
    )
    update.message.reply_text(message)
    return ASK_AGE


def handle_cancel(update, context):
    """Allow the user to cancel the conversation"""
    update.message.reply_text("Okay, cancelled. Send /start to begin or /plan to generate a meal plan.")
    return ConversationHandler.END


def answer_food_query(gemini_key, query):
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')

        prompt = f"""You are a helpful Indian food and nutrition expert assistant.

A user has asked you this question related to food:
"{query}"

Please provide a helpful, concise, and accurate response. If it's a recipe request, include ingredients and brief cooking steps. 
If it's about nutrition, provide relevant nutritional information. Keep the response friendly and informative.
Use emojis where appropriate to make it engaging."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "quota" in err_msg.lower():
            return "Sorry, I'm temporarily unable to answer queries (API quota exceeded). Please try again later."
        return f"Sorry, I encountered an error processing your query. Please try again later."




def _verify_url(url, timeout=5):
    """Return True if URL appears reachable. Special-case YouTube via oEmbed."""
    try:
        if "youtube.com" in url or "youtu.be" in url:
            # Use oEmbed to verify YouTube video availability
            oembed = f"https://www.youtube.com/oembed?url={requests.utils.requote_uri(url)}&format=json"
            r = requests.get(oembed, timeout=timeout)
            return r.status_code == 200

        # Generic check: HEAD then GET fallback
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        if r.status_code and r.status_code < 400:
            return True
        # Some servers disallow HEAD; try GET
        r = requests.get(url, allow_redirects=True, timeout=timeout)
        return r.status_code < 400
    except Exception:
        return False


def _clean_response_links(text):
    """Remove unreachable URLs from the text. Returns (cleaned_text, removed_urls_list)."""
    url_regex = r"(?i)\b((?:https?://|www\.)[^\s<>]+)"
    matches = re.findall(url_regex, text)
    if not matches:
        return text, []

    removed = []
    cleaned = text
    for raw_url in matches:
        url = raw_url
        if url.startswith("www."):
            url = "http://" + url

        ok = _verify_url(url)
        if not ok:
            removed.append(raw_url)
            # remove the URL from text
            cleaned = cleaned.replace(raw_url, "[removed unavailable link]")

    return cleaned, removed


def search_youtube(query, api_key, max_results=1):
    """Search YouTube for `query` using YouTube Data API v3 and return first video URL or None."""
    try:
        if not api_key:
            # No API key: try to use yt_dlp as a no-key fallback
            try:
                from yt_dlp import YoutubeDL
            except Exception:
                return None

            try:
                ydl_opts = {'quiet': True, 'skip_download': True}
                with YoutubeDL(ydl_opts) as ydl:
                    # ytsearch1: uses YouTube search and returns the first result
                    info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                    entries = info.get('entries') or []
                    if not entries:
                        return None
                    vid = entries[0]
                    video_id = vid.get('id')
                    if not video_id:
                        return None
                    return f'https://www.youtube.com/watch?v={video_id}'
            except Exception:
                return None

        # Prefer official YouTube Data API when api_key is present
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'key': api_key,
        }
        r = requests.get('https://www.googleapis.com/youtube/v3/search', params=params, timeout=6)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data.get('items', [])
        if not items:
            return None
        video_id = items[0].get('id', {}).get('videoId')
        if not video_id:
            return None
        return f'https://www.youtube.com/watch?v={video_id}'
    except Exception:
        return None


def handle_food_query(update, context):
    """Handle general text messages as food/recipe queries"""
    user_message = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Ignore very short messages
    if len(user_message) < 3:
        return
    
    try:
        # Show typing indicator
        update.message.chat.send_action("typing")
        
        # Generate response
        gemini_key = load_api_key()
        response = answer_food_query(gemini_key, user_message)

        # Verify and strip invalid links from assistant response
        cleaned, removed_urls = _clean_response_links(response)
        print(f"DEBUG: user_message='{user_message[:80]}' removed_urls={removed_urls}")
        appended_verified = None

        # If links were removed or user explicitly asked for a video/link, try to find a verified YouTube link
        user_wants_video = any(k in user_message.lower() for k in ("video", "link", "youtube", "youtube.com", "youtu.be"))
        if removed_urls or user_wants_video:
            youtube_api_key = os.getenv('YOUTUBE_API_KEY')
            if youtube_api_key:
                print("DEBUG: YOUTUBE_API_KEY present, using YouTube Data API for search")
            else:
                print("DEBUG: No YOUTUBE_API_KEY, attempting yt-dlp fallback search")

            verified = search_youtube(user_message, os.getenv('YOUTUBE_API_KEY'))
            if verified:
                appended_verified = verified
                cleaned += f"\n\n🔗 Verified video link: {verified}"
                print(f"DEBUG: search_youtube found: {verified}")
            else:
                print("DEBUG: search_youtube returned no result")
                if removed_urls:
                    cleaned += "\n\n⚠️ Note: Removed unavailable link(s) from the response. I couldn't find a verified video for your query."

        # Split message if too long
        if len(cleaned) > 4096:
            chunks = [cleaned[i:i+4096] for i in range(0, len(cleaned), 4096)]
            for chunk in chunks:
                update.message.reply_text(chunk)
        else:
            update.message.reply_text(cleaned)
        
        print(f"   ✅ Answered food query from user {user_id}: '{user_message[:50]}...'")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"   ❌ Error answering food query from user {user_id}: {str(e)}")
        print(f"   Details: {error_details}")
        update.message.reply_text("Sorry, I couldn't process your query. Please try again!")


def send_daily_meal_plans():
    """Send meal plans to all users with profiles at scheduled time"""
    global bot_instance, user_profiles
   
    print(f"\n{'='*60}")
    print(f"📅 Scheduled task triggered at {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"{'='*60}")
   
    if not bot_instance:
        print("❌ ERROR: Bot instance not available for scheduled meal plans")
        return
   
    # 🔧 FIX 1: Load profiles from disk before checking
    load_profiles_from_disk()
   
    if not user_profiles:
        print("⚠️  WARNING: No users with profiles to send meal plans to")
        print("   Users need to complete their profile with /start first")
        return
   
    try:
        gemini_key = load_api_key()
        print(f"✅ Found {len(user_profiles)} user(s) with profiles")
        print(f"📤 Starting to send meal plans...\n")
       
        for user_id, profile in user_profiles.items():
            try:
                # 🔧 FIX 2: Convert user_id to string for consistency
                user_id_str = str(user_id)
               
                # Generate meal plan
                plan = generate_meal_plan(gemini_key, profile)
               
                # Send message to user
                message = (
                    "🌙 Good Evening! Here's your daily meal plan for tomorrow:\n\n"
                    f"{plan}\n\n"
                    "💡 Send /plan anytime to generate a new meal plan!"
                )
               
                # Split message if too long
                if len(message) > 4096:
                    chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
                    for chunk in chunks:
                        bot_instance.send_message(chat_id=user_id, text=chunk)
                else:
                    bot_instance.send_message(chat_id=user_id, text=message)
               
                print(f"   ✅ Meal plan sent to user {user_id}")
               
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"   ❌ Error sending meal plan to user {user_id}")
                print(f"   Error: {str(e)}")
                print(f"   Details: {error_details}")
                # Try to notify user about the error
                try:
                    bot_instance.send_message(
                        chat_id=user_id,
                        text=f"Sorry, there was an error generating your daily meal plan. Please try /plan to generate one manually."
                    )
                except Exception as notify_error:
                    print(f"   ❌ Could not notify user about error: {str(notify_error)}")
       
        print(f"{'='*60}")
        print("✅ Daily meal plan distribution completed")
        print(f"{'='*60}\n")
       
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ CRITICAL ERROR in scheduled meal plan task:")
        print(f"   Error: {str(e)}")
        print(f"   Details: {error_details}")
        print(f"{'='*60}\n")

def run_telegram_bot():
    """Run the Telegram bot"""
    global bot_instance
    
    load_dotenv()
    load_profiles_from_disk()
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
    
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher
    
    # Store bot instance globally for scheduled tasks
    bot_instance = updater.bot

    # Conversation handler for profile collection
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", handle_start),
            CommandHandler("profile", handle_profile)
        ],
        states={
            ASK_AGE: [
                MessageHandler(Filters.text & ~Filters.command, handle_age)
            ],
            ASK_WEIGHT: [
                MessageHandler(Filters.text & ~Filters.command, handle_weight)
            ],
            ASK_HEIGHT: [
                MessageHandler(Filters.text & ~Filters.command, handle_height)
            ],
        },
        fallbacks=[CommandHandler("cancel", handle_cancel)],
    )

    # Add command handlers
    dp.add_handler(CommandHandler("plan", handle_plan))
    dp.add_handler(CommandHandler("test_schedule", handle_test_schedule))  # For testing
    dp.add_handler(conv_handler)
    
    # Add handler for general food/recipe queries (must be after conversation handler)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_food_query))

    # Set up scheduler for daily meal plans at 12:07 PM IST
    ist_timezone = pytz.timezone('Asia/Kolkata')
    scheduler = BackgroundScheduler(timezone=ist_timezone)
    
    scheduler.add_job(
        send_daily_meal_plans,
        trigger='cron',
        hour=20,   # 12 PM IST
        minute=51,  # 12:07 PM IST
        id='daily_meal_plans',
        name='Send daily meal plans to all users',
        replace_existing=True
    )
    
    scheduler.start()
    
    # Log scheduler status
    jobs = scheduler.get_jobs()
    print("\n" + "="*60)
    print("🤖 Starting Indian Meal Planner Bot...")
    print("="*60)
    print(f"✅ Bot instance created")
    print(f"✅ Scheduler started with {len(jobs)} job(s)")
    for job in jobs:
        next_run = job.next_run_time
        if next_run:
            next_run_ist = next_run.astimezone(ist_timezone)
            print(f"   📅 Next scheduled run: {next_run_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
        else:
            print(f"   ⚠️  Job '{job.name}' has no next run time")
    print(f"📊 Current time: {datetime.now(ist_timezone).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("="*60)
    print("The bot is now running. Users can interact with it on Telegram.")
    print("Send /start in Telegram to begin.")
    print("📅 Daily meal plans will be sent automatically at 12:07 PM IST")
    print("🧪 Use /test_schedule to manually test the scheduled task")
    print("Press Ctrl+C to stop the bot.\n")
    
    updater.start_polling()
    updater.idle()
    
    # Cleanup
    scheduler.shutdown()


def main():
    """Main function to start the Telegram bot"""
    try:
        run_telegram_bot()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    except KeyboardInterrupt:
        print("\n\nBot stopped by user.")


if __name__ == "__main__":
    main()
