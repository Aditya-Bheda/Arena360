# frontend/views.py
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import razorpay
import json
import hmac
import hashlib
import requests
import base64

from .models import (
    UserProfile,
    Sport,
    SportsClub,
    Booking,
    Favourite
)
from .forms import SportsClubForm, ProfileEditForm
from django.db.models import Count, Sum
from django.core.exceptions import FieldDoesNotExist
import logging

logger = logging.getLogger(__name__)

# Initialize Razorpay client
try:
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and settings.RAZORPAY_KEY_ID != "rzp_test_xxx":
        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    else:
        razorpay_client = None
except (ImportError, AttributeError, Exception):
    razorpay_client = None


# Message Central API Functions
def get_message_central_token():
    """Get authentication token from Message Central API"""
    try:
        customer_id = getattr(settings, 'MESSAGE_CENTRAL_CUSTOMER_ID', None)
        key = getattr(settings, 'MESSAGE_CENTRAL_KEY', None)
        country_code = getattr(settings, 'MESSAGE_CENTRAL_COUNTRY_CODE', '91')
        email = getattr(settings, 'MESSAGE_CENTRAL_EMAIL', None)
        
        if not all([customer_id, key, email]):
            logger.warning("Message Central credentials not configured")
            return None
        
        # Check if key is already Base64 encoded, if not encode it
        # Base64 strings typically don't contain spaces and have specific character set
        try:
            # Try to decode - if it works, it's already Base64
            base64.b64decode(key)
            encoded_key = key
        except:
            # If decoding fails, it's plain text - encode it
            encoded_key = base64.b64encode(key.encode('utf-8')).decode('utf-8')
        
        url = f"https://cpaas.messagecentral.com/auth/v1/authentication/token"
        params = {
            'customerId': customer_id,
            'key': encoded_key,
            'scope': 'NEW',
            'country': country_code,
            'email': email
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('authToken')
        else:
            logger.error(f"Message Central token request failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting Message Central token: {str(e)}")
        return None


def send_sms_via_message_central(phone_number, message_text):
    """Send SMS using Message Central API"""
    try:
        auth_token = get_message_central_token()
        if not auth_token:
            logger.warning("Could not get Message Central auth token")
            return False
        
        sender_id = getattr(settings, 'MESSAGE_CENTRAL_SENDER_ID', 'ARENA360')
        country_code = getattr(settings, 'MESSAGE_CENTRAL_COUNTRY_CODE', '91')
        
        # Clean phone number (remove any non-digits)
        phone_clean = ''.join(filter(str.isdigit, phone_number))
        if not phone_clean:
            logger.error(f"Invalid phone number: {phone_number}")
            return False
        
        url = "https://cpaas.messagecentral.com/verification/v3/send"
        params = {
            'countryCode': country_code,
            'flowType': 'SMS',
            'mobileNumber': phone_clean,
            'senderId': sender_id,
            'type': 'SMS',
            'message': message_text,
            'messageType': 'TRANSACTION'
        }
        
        headers = {
            'authToken': auth_token
        }
        
        response = requests.post(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"SMS sent successfully to {phone_clean}")
            return True
        else:
            logger.error(f"Message Central SMS send failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending SMS via Message Central: {str(e)}")
        return False


def send_booking_confirmation_sms(booking):
    """Send booking confirmation SMS to user"""
    try:
        # Format booking details for SMS
        club_name = booking.club.club_name
        sport_name = booking.sport.name
        date_str = booking.date.strftime("%d-%m-%Y")
        time_str = f"{booking.start_time.strftime('%I:%M %p')} - {booking.end_time.strftime('%I:%M %p')}"
        amount = booking.amount
        
        message = f"Your booking at {club_name} is confirmed!\n\nSport: {sport_name}\nDate: {date_str}\nTime: {time_str}\nAmount: ₹{amount}\n\nThank you for choosing Arena360!"
        
        # Send SMS to booking phone number
        if booking.phone:
            return send_sms_via_message_central(booking.phone, message)
        else:
            logger.warning(f"No phone number found for booking {booking.id}")
            return False
    except Exception as e:
        logger.error(f"Error in send_booking_confirmation_sms: {str(e)}")
        return False


def home(request):
    return render(request, "dashboard.html")


# -------------------------
# Landing + Dashboard
# -------------------------
def dashboard(request):
    """
    Landing page (public). According to your last note, this is the landing page
    a user sees (with 'Become a Partner', profile button etc.).
    """
    return render(request, "dashboard.html")


@login_required(login_url="login")
def user_dashboard(request):
    """
    Shows approved clubs to logged in users.
    """
    clubs = SportsClub.objects.filter(approved=True).order_by("-created_at")
    return render(request, "user_dashboard.html", {"clubs": clubs})


# -------------------------
# Authentication
# -------------------------
from django.shortcuts import redirect

def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            
            # Get profile from database (signal should have created it, but ensure it exists)
            try:
                profile = UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                # If profile doesn't exist, create it with default False
                profile = UserProfile.objects.create(user=user, is_partner=False)
            
            # Refresh from database to ensure we have the latest data
            profile.refresh_from_db()
            
            # Redirect based on role - check is_partner status from database
            if profile.is_partner:
                return redirect("partner-dashboard")
            
            return redirect("user-dashboard")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "login.html")




def logout_view(request):
    logout(request)
    return redirect("home")  # or "dashboard" depending on your urls; 'home' below maps to dashboard


def register_page(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        is_partner = request.POST.get("is_partner") == "on"

        if not (full_name and email and phone and password):
            messages.error(request, "All fields are required.")
            return render(request, "register.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "register.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, "register.html")

        username = email.split("@")[0]
        # ensure username unique
        base = username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{i}"
            i += 1

        user = User.objects.create_user(username=username, email=email, password=password, first_name=full_name)
        
        # Get or create profile (signal may have already created it)
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.is_partner = is_partner  # Set partner status
        profile.save()  # Explicitly save to ensure it's stored in database
        
        # Verify the save worked
        profile.refresh_from_db()
        
        login(request, user)
        # Redirect partner to partner dashboard
        return redirect("partner-dashboard" if profile.is_partner else "user-dashboard")

    return render(request, "register.html")


# -------------------------
# Partner (owner) flows
# -------------------------
@login_required(login_url="login")
def partner_register(request):
    """
    Add club (partner registration). Uses SportsClubForm.
    """
    if request.method == "POST":
        form = SportsClubForm(request.POST, request.FILES)
        if form.is_valid():
            club = form.save(commit=False)
            club.owner = request.user
            club.approved = False
            club.save()
            form.save_m2m()
            messages.success(request, "Club submitted — waiting for admin approval.")
            return redirect("partner-dashboard")
        messages.error(request, "Please correct the errors below.")
    else:
        form = SportsClubForm()
    return render(request, "partner_registration.html", {"form": form})


# @login_required(login_url="login")
# def partner_dashboard(request):
#     clubs = SportsClub.objects.filter(owner=request.user).order_by("-created_at")
#     return render(request, "partner_dashboard.html", {"clubs": clubs})


@login_required(login_url="login")
def partner_clubs(request):
    """
    Alias listing for partner's clubs (same as dashboard for partner).
    """
    return partner_dashboard(request)


@login_required(login_url="login")
def add_club(request):
    # alias to partner_register to match URL naming conventions
    return partner_register(request)


@login_required
def edit_club(request, club_id):
    club = get_object_or_404(SportsClub, id=club_id, owner=request.user)

    if request.method == "POST":
        form = SportsClubForm(request.POST, request.FILES, instance=club)
        if form.is_valid():
            form.save()
            messages.success(request, "Club updated successfully.")
            return redirect("partner-dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SportsClubForm(instance=club)

    return render(request, "edit_club.html", {"club": club, "form": form})


# -------------------------
# Profile
# -------------------------
@login_required(login_url="login")
def edit_profile(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        # You probably have a custom ProfileEditForm: adapt if necessary
        form = ProfileEditForm(request.POST, instance=user, profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("user-dashboard")
        messages.error(request, "Please correct the errors.")
    else:
        form = ProfileEditForm(instance=user, profile=profile)

    return render(request, "edit_profile.html", {"form": form})


# -------------------------
# Favourites
# -------------------------
@login_required
def toggle_favourite(request, club_id):
    club = get_object_or_404(SportsClub, id=club_id)
    fav, created = Favourite.objects.get_or_create(user=request.user, club=club)

    if not created:
        fav.delete()   # remove favourite

    return redirect(request.META.get("HTTP_REFERER", "user-dashboard"))


@login_required(login_url="login")
def favourites(request):
    favs = Favourite.objects.filter(user=request.user).select_related("club")
    return render(request, "favourites.html", {"favs": favs})


# -------------------------
# Club details
# -------------------------
def club_details(request, club_id):
    club = get_object_or_404(SportsClub, id=club_id)
    is_favourite = False
    if request.user.is_authenticated:
        is_favourite = Favourite.objects.filter(user=request.user, club=club).exists()
    return render(request, "club_details.html", {"club": club, "is_favourite": is_favourite})


# -------------------------
# Booking views (clean — no razorpay, no locking)
# -------------------------
@login_required
def club_booking(request, club_id):
    club = get_object_or_404(SportsClub, id=club_id, approved=True)

    sports = club.sports.all()
    sport_id = request.GET.get("sport")
    date_str = request.GET.get("date")

    # Calculate min and max dates (today to 30 days in future)
    today = timezone.now().date()
    max_date = today + timedelta(days=30)
    min_date_str = today.isoformat()
    max_date_str = max_date.isoformat()

    availability = None
    slot_date = None
    error_message = None

    if sport_id and date_str:
        try:
            slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Validate date is not in the past
            if slot_date < today:
                error_message = "Cannot book for past dates. Please select today or a future date."
            # Validate date is within 30 days
            elif slot_date > max_date:
                error_message = f"Bookings are only available for the next 30 days. Maximum date is {max_date.strftime('%B %d, %Y')}."
            else:
                sport = get_object_or_404(Sport, id=sport_id)

                # generate all slots
                all_slots = club.generate_slots_for_date(slot_date)

                # check booked slots
                booked = Booking.objects.filter(
                    club=club, sport=sport, date=slot_date
                ).values_list("start_time", flat=True)

                availability = []
                now = timezone.now()
                is_today = slot_date == today
                
                for start, end in all_slots:
                    # For today's date, filter out past time slots
                    if is_today:
                        slot_datetime = datetime.combine(slot_date, start)
                        slot_datetime = timezone.make_aware(slot_datetime)
                        if slot_datetime < now:
                            continue  # Skip past slots
                    
                    availability.append({
                        "start": start.strftime("%H:%M"),
                        "end": end.strftime("%H:%M"),
                        "available": start not in booked
                    })
        except ValueError:
            error_message = "Invalid date format."

    return render(request, "club_booking.html", {
        "club": club,
        "sports": sports,
        "selected_sport_id": sport_id,
        "slot_date": date_str,
        "availability": availability,
        "min_date": min_date_str,
        "max_date": max_date_str,
        "error_message": error_message
    })



@login_required(login_url="login")
def submit_booking(request, club_id):
    """
    Creates a Booking record (POST). Expects:
      - sport (GET param or POST hidden)
      - date (GET param or POST)
      - start (GET param or POST) "HH:MM"
      - end (GET param or POST) "HH:MM"
      - name (POST)
      - phone (POST)
    After successful booking redirect to booking_confirmation.
    """
    club = get_object_or_404(SportsClub, id=club_id, approved=True)

    # Read params from GET (when user clicks slot -> usually links pass sport/date/start/end)
    sport_id = request.GET.get("sport") or request.POST.get("sport")
    date_str = request.GET.get("date") or request.POST.get("date")
    start_str = request.GET.get("start") or request.POST.get("start")
    end_str = request.GET.get("end") or request.POST.get("end")

    if not (sport_id and date_str and start_str and end_str):
        messages.error(request, "Missing slot information. Please re-select slot.")
        return redirect("club-booking", club_id=club.id)

    try:
        sport = Sport.objects.get(id=int(sport_id))
    except Sport.DoesNotExist:
        messages.error(request, "Selected sport not found.")
        return redirect("club-booking", club_id=club.id)

    try:
        slot_date = datetime.fromisoformat(date_str).date()
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        
        # Validate date is not in the past
        today = timezone.now().date()
        if slot_date < today:
            messages.error(request, "Cannot book for past dates.")
            return redirect("club-booking", club_id=club.id)
        
        # Validate date is within 30 days
        max_date = today + timedelta(days=30)
        if slot_date > max_date:
            messages.error(request, f"Bookings are only available for the next 30 days.")
            return redirect("club-booking", club_id=club.id)
        
        # For today's bookings, validate time is not in the past
        if slot_date == today:
            now = timezone.now()
            slot_datetime = datetime.combine(slot_date, start_time)
            slot_datetime = timezone.make_aware(slot_datetime)
            if slot_datetime < now:
                messages.error(request, "Cannot book past time slots.")
                return redirect("club-booking", club_id=club.id)
                
    except Exception:
        messages.error(request, "Invalid date/time format.")
        return redirect("club-booking", club_id=club.id)

    # If POST -> create booking
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not (name and phone):
            messages.error(request, "Please enter name and phone.")
            # Calculate amount for display
            start_dt = datetime.combine(slot_date, start_time)
            end_dt = datetime.combine(slot_date, end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            duration_hours = (end_dt - start_dt).total_seconds() / 3600
            booking_amount = float(club.price_per_hour) * duration_hours
            return render(request, "confirm_and_pay.html", {
                "club": club,
                "sport": sport,
                "date": slot_date,
                "start": start_str,
                "end": end_str,
                "amount": booking_amount
            })

        # Check if a booking already exists for same club,sport,date,start
        exists = Booking.objects.filter(
            club=club,
            sport=sport,
            date=slot_date,
            start_time=start_time
        ).exists()

        if exists:
            messages.error(request, "Slot already taken. Please choose another slot.")
            return redirect(f"{reverse('club-booking', args=[club.id])}?sport={sport.id}&date={slot_date.isoformat()}")

        # Calculate booking amount
        start_dt = datetime.combine(slot_date, start_time)
        end_dt = datetime.combine(slot_date, end_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        booking_amount = float(club.price_per_hour) * duration_hours
        amount_in_paise = int(booking_amount * 100)  # Razorpay expects amount in paise

        # Create booking with pending payment status
        booking = Booking.objects.create(
            user=request.user,
            club=club,
            sport=sport,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            name=name,
            phone=phone,
            amount=booking_amount,
            payment_status='pending'
        )

        # Create Razorpay order if Razorpay is configured
        if razorpay_client:
            try:
                razorpay_order = razorpay_client.order.create({
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'receipt': f'booking_{booking.id}',
                    'notes': {
                        'booking_id': booking.id,
                        'club': club.club_name,
                        'sport': sport.name,
                    }
                })
                booking.razorpay_order_id = razorpay_order['id']
                booking.save()

                # Return combined confirm and pay page with Razorpay
                return render(request, "confirm_and_pay.html", {
                    "club": club,
                    "sport": sport,
                    "date": slot_date,
                    "start": start_str,
                    "end": end_str,
                    "booking": booking,
                    "razorpay_order_id": razorpay_order['id'],
                    "amount": booking_amount,
                    "amount_in_paise": amount_in_paise,
                    "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                })
            except Exception as e:
                messages.error(request, f"Payment gateway error: {str(e)}")
                booking.delete()  # Delete booking if payment order creation fails
                return redirect("club-booking", club_id=club.id)
        else:
            # If Razorpay not configured, mark as paid and proceed
            booking.payment_status = 'paid'
            booking.save()
            # Send confirmation SMS
            send_booking_confirmation_sms(booking)
            return redirect(reverse("booking-confirmation") + f"?id={booking.id}")

    # Calculate amount for display
    start_dt = datetime.combine(slot_date, start_time)
    end_dt = datetime.combine(slot_date, end_time)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    duration_hours = (end_dt - start_dt).total_seconds() / 3600
    booking_amount = float(club.price_per_hour) * duration_hours

    # GET -> show combined confirm and pay form
    return render(request, "confirm_and_pay.html", {
        "club": club,
        "sport": sport,
        "date": slot_date,
        "start": start_str,
        "end": end_str,
        "amount": booking_amount
    })


# -------------------------
# My Bookings + Confirmation
# -------------------------
@login_required(login_url="login")
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by("-date", "-start_time")
    return render(request, "my_bookings.html", {"bookings": bookings})


def booking_confirmation(request):
    booking_id = request.GET.get("id")
    booking = None
    if booking_id:
        # Only show booking if it belongs to the logged-in user
        if request.user.is_authenticated:
            booking = Booking.objects.filter(id=booking_id, user=request.user).first()
        else:
            booking = Booking.objects.filter(id=booking_id).first()
    return render(request, "booking_success.html", {"booking": booking})


@csrf_exempt
def payment_callback(request):
    """Handle Razorpay payment callback"""
    if request.method == "POST":
        try:
            # Get payment details from Razorpay
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            booking_id = request.POST.get('booking_id')

            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, booking_id]):
                messages.error(request, "Missing payment details. Please try again.")
                return redirect("home")

            booking = Booking.objects.get(id=booking_id, razorpay_order_id=razorpay_order_id)

            # Verify signature
            if razorpay_client:
                params_dict = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                }
                try:
                    razorpay_client.utility.verify_payment_signature(params_dict)
                    # Payment successful
                    booking.razorpay_payment_id = razorpay_payment_id
                    booking.razorpay_signature = razorpay_signature
                    booking.payment_status = 'paid'
                    booking.save()
                    # Send confirmation SMS
                    send_booking_confirmation_sms(booking)
                    messages.success(request, "Payment successful! Your booking is confirmed.")
                    return redirect(reverse('booking-confirmation') + f'?id={booking.id}')
                except razorpay.errors.SignatureVerificationError:
                    booking.payment_status = 'failed'
                    booking.save()
                    messages.error(request, "Payment verification failed. Please contact support.")
                    return redirect("home")
            else:
                # If Razorpay not configured, mark as paid
                booking.payment_status = 'paid'
                booking.save()
                # Send confirmation SMS
                send_booking_confirmation_sms(booking)
                messages.success(request, "Booking confirmed!")
                return redirect(reverse('booking-confirmation') + f'?id={booking.id}')

        except Booking.DoesNotExist:
            messages.error(request, "Booking not found.")
            return redirect("home")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect("home")

    messages.error(request, "Invalid request.")
    return redirect("home")


# -------------------------
# Utility (optional)
# -------------------------
def generate_time_slots_for_display(open_time, close_time, duration_minutes=60):
    """
    Utility if you need to build front-end slots outside model. Not used directly here
    because we rely on SportsClub.generate_slots_for_date.
    """
    slots = []
    now = timezone.localtime()
    today = now.date()
    start_dt = datetime.combine(today, open_time)
    end_dt = datetime.combine(today, close_time)
    step = timedelta(minutes=duration_minutes)
    cur = start_dt
    while cur + step <= end_dt:
        slots.append((cur.time(), (cur + step).time()))
        cur += step
    return slots

def confirm_booking(request, club_id):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        sport_id = request.POST.get("sport_id")
        date_str = request.POST.get("date")
        start_str = request.POST.get("start")
        end_str = request.POST.get("end")

        club = get_object_or_404(SportsClub, id=club_id)
        sport = get_object_or_404(Sport, id=sport_id)

        try:
            # Parse date and time
            if isinstance(date_str, str):
                slot_date = datetime.fromisoformat(date_str).date()
            else:
                slot_date = date_str
            
            if isinstance(start_str, str):
                start_time = datetime.strptime(start_str, "%H:%M").time()
            else:
                start_time = start_str
                
            if isinstance(end_str, str):
                end_time = datetime.strptime(end_str, "%H:%M").time()
            else:
                end_time = end_str
            
            # Validate date is not in the past
            today = timezone.now().date()
            if slot_date < today:
                return render(request, "booking_failed.html", {"message": "Cannot book for past dates."})
            
            # Validate date is within 30 days
            max_date = today + timedelta(days=30)
            if slot_date > max_date:
                return render(request, "booking_failed.html", {"message": "Bookings are only available for the next 30 days."})
            
            # For today's bookings, validate time is not in the past
            if slot_date == today:
                now = timezone.now()
                slot_datetime = datetime.combine(slot_date, start_time)
                slot_datetime = timezone.make_aware(slot_datetime)
                if slot_datetime < now:
                    return render(request, "booking_failed.html", {"message": "Cannot book past time slots."})
        except Exception as e:
            return render(request, "booking_failed.html", {"message": "Invalid date/time format."})

        # Prevent double booking
        if Booking.objects.filter(club=club, sport=sport, date=slot_date, start_time=start_time).exists():
            return render(request, "booking_failed.html", {"message": "Slot already booked!"})

        booking = Booking.objects.create(
            user=request.user,
            club=club,
            sport=sport,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            name=name,
            phone=phone
        )

        return redirect(f"/booking-success/?id={booking.id}")

    return JsonResponse({"error": "Invalid request"})

@login_required
def booking_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "booking_success.html", {"booking": booking})


def profile(request):
    profile = request.user.profile  # auto created

    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")

        # update Django user table
        request.user.first_name = name
        request.user.save()

        # update profile table
        profile.phone = phone
        profile.save()

        return redirect("profile")

    return render(request, "profile.html", {
        "profile": profile,
        "user": request.user,
    })

def help_support(request):
    return render(request, "help_support.html")

@login_required
def update_role(request):
    if request.method == "POST":
        request.user.profile.is_partner = request.POST.get("is_partner") == "on"
        request.user.profile.save()

        return redirect("partner-dashboard" if request.user.profile.is_partner else "user-dashboard")

@login_required
def partner_dashboard(request):
    # Ensure profile exists
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.is_partner:
        return redirect("user-dashboard")
    clubs = SportsClub.objects.filter(owner=request.user).order_by("-created_at")
    bookings = Booking.objects.filter(club__owner=request.user).select_related('club', 'sport')

    # Aggregates
    total_bookings = bookings.count()
    total_clubs = clubs.count()

    # Calculate total earnings from bookings (price_per_hour * duration in hours)
    total_earnings = 0
    for booking in bookings:
        start_dt = datetime.combine(booking.date, booking.start_time)
        end_dt = datetime.combine(booking.date, booking.end_time)
        # Handle case where end_time might be next day
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        total_earnings += float(booking.club.price_per_hour) * duration_hours

    # Bookings by date for line chart
    bookings_by_date = bookings.values('date').annotate(cnt=Count('id')).order_by('date')
    booking_labels = [b['date'].isoformat() for b in bookings_by_date]
    booking_data = [b['cnt'] for b in bookings_by_date]

    # Revenue by date for earnings chart
    revenue_by_date = {}
    for booking in bookings:
        date_str = booking.date.isoformat()
        start_dt = datetime.combine(booking.date, booking.start_time)
        end_dt = datetime.combine(booking.date, booking.end_time)
        # Handle case where end_time might be next day
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        revenue = float(booking.club.price_per_hour) * duration_hours
        revenue_by_date[date_str] = revenue_by_date.get(date_str, 0) + revenue
    
    revenue_labels = sorted(revenue_by_date.keys())
    revenue_data = [round(revenue_by_date[label], 2) for label in revenue_labels]

    return render(request, "partner_dashboard.html", {
        "clubs": clubs,
        "bookings": bookings,
        "total_bookings": total_bookings,
        "total_clubs": total_clubs,
        "total_earnings": round(total_earnings, 2),
        "chart_labels_json": json.dumps(booking_labels),
        "chart_data_json": json.dumps(booking_data),
        "revenue_labels_json": json.dumps(revenue_labels),
        "revenue_data_json": json.dumps(revenue_data),
        "total_bookings_json": json.dumps([total_bookings]),
        "total_earnings_json": json.dumps([round(total_earnings, 2)]),
    })


@login_required(login_url="login")
def partner_bookings(request):
    # Ensure profile exists
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.is_partner:
        return redirect('user-dashboard')
    
    bookings = Booking.objects.filter(club__owner=request.user).select_related('club', 'sport', 'user')
    
    # Filter by date category
    filter_type = request.GET.get('filter', 'all')
    today = timezone.now().date()
    
    if filter_type == 'today':
        bookings = bookings.filter(date=today)
    elif filter_type == 'past':
        bookings = bookings.filter(date__lt=today)
    elif filter_type == 'future':
        bookings = bookings.filter(date__gt=today)
    # 'all' shows everything
    
    bookings = bookings.order_by('-date', '-start_time')
    
    return render(request, 'my_bookings.html', {
        'bookings': bookings,
        'filter_type': filter_type,
        'is_partner_view': True
    })


@login_required(login_url="login")
def partner_earnings(request):
    # Ensure profile exists
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.is_partner:
        return redirect('user-dashboard')
    # Placeholder earnings view — uses same aggregates as dashboard
    bookings = Booking.objects.filter(club__owner=request.user)
    try:
        Booking._meta.get_field('amount')
    except FieldDoesNotExist:
        total_earnings = 0
    else:
        total_earnings = bookings.aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'partner_earnings.html', {'total_earnings': total_earnings})

def partner_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("partner-dashboard")
        else:
            return render(request, "partner_login.html", {
                "error": "Invalid credentials"
            })

    return render(request, "partner_login.html")