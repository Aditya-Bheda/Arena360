# frontend/views.py
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    UserProfile,
    Sport,
    SportsClub,
    Booking,
    Favourite
)
from .forms import SportsClubForm, ProfileEditForm

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
def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")  # can be username or email depending on your form
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("user-dashboard")
        messages.error(request, "Invalid username or password")
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
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.save()

        login(request, user)
        return redirect("user-dashboard")

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


@login_required(login_url="login")
def partner_dashboard(request):
    clubs = SportsClub.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "partner_dashboard.html", {"clubs": clubs})


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
        club.club_name = request.POST.get("club_name")
        club.location = request.POST.get("location")
        club.contact_number = request.POST.get("contact_number")
        club.available_courts = request.POST.get("available_courts", club.available_courts)
        club.price_per_hour = request.POST.get("price_per_hour", club.price_per_hour)
        club.save()
        return redirect("partner-dashboard")

    return render(request, "edit_club.html", {"club": club})


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

    availability = None
    slot_date = None

    if sport_id and date_str:
        slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        sport = get_object_or_404(Sport, id=sport_id)

        # generate all slots
        all_slots = club.generate_slots_for_date(slot_date)

        # check booked slots
        booked = Booking.objects.filter(
            club=club, sport=sport, date=slot_date
        ).values_list("start_time", flat=True)

        availability = []
        for start, end in all_slots:
            availability.append({
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
                "available": start not in booked
            })

    return render(request, "club_booking.html", {
        "club": club,
        "sports": sports,
        "selected_sport_id": sport_id,
        "slot_date": date_str,
        "availability": availability
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
    except Exception:
        messages.error(request, "Invalid date/time format.")
        return redirect("club-booking", club_id=club.id)

    # If POST -> create booking
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not (name and phone):
            messages.error(request, "Please enter name and phone.")
            return render(request, "submit_booking.html", {
                "club": club,
                "sport": sport,
                "date": slot_date,
                "start": start_str,
                "end": end_str
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

        # Create booking (simple, no payment)
        b = Booking.objects.create(
            user=request.user,
            club=club,
            sport=sport,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            name=name,
            phone=phone
        )

        # Success -> show booking confirmation page
        return redirect(reverse("booking-confirmation") + f"?id={b.id}")

    # GET -> show confirm form
    return render(request, "submit_booking.html", {
        "club": club,
        "sport": sport,
        "date": slot_date,
        "start": start_str,
        "end": end_str
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
        booking = Booking.objects.filter(id=booking_id).first()
    return render(request, "booking_success.html", {"booking": booking})


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
        date = request.POST.get("date")
        start = request.POST.get("start")
        end = request.POST.get("end")

        club = get_object_or_404(SportsClub, id=club_id)
        sport = get_object_or_404(Sport, id=sport_id)

        # Prevent double booking
        if Booking.objects.filter(club=club, sport=sport, date=date, start_time=start).exists():
            return render(request, "booking_failed.html", {"message": "Slot already booked!"})

        booking = Booking.objects.create(
            user=request.user,
            club=club,
            sport=sport,
            date=date,
            start_time=start,
            end_time=end,
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