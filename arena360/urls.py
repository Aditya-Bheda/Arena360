# from django.contrib import admin
# from django.urls import path
# from frontend import views
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [

#     # ---------- Admin ----------
#     path('admin/', admin.site.urls),

#     # ---------- Authentication ----------
#     path('login/', views.login_page, name='login'),
#     path('register/', views.register_page, name='register'),
#     path('logout/', views.logout_view, name='logout'),

#     # ---------- User Dashboard ----------
#     path('user-dashboard/', views.user_dashboard, name='user-dashboard'),

#     # ---------- Partner Dashboard ----------
#     path('partner-dashboard/', views.partner_dashboard, name='partner-dashboard'),
#     path('partner/add-club/', views.add_club, name='add-club'),
#     path('partner/clubs/', views.partner_clubs, name='partner-clubs'),
#     path('partner/club/<int:club_id>/edit/', views.edit_club, name='edit-club'),

#     # ---------- Club Browsing ----------
#     path('', views.homepage, name='home'),
#     path('clubs/', views.all_clubs, name='all-clubs'),
#     path('club/<int:club_id>/', views.club_detail, name='club-detail'),

#     # ---------- Booking (Simple — no lock-slot, no Razorpay) ----------
#     path("club/<int:club_id>/book/", views.club_booking, name="club-booking"),
#     path("club/<int:club_id>/book/submit/", views.submit_booking, name="submit-booking"),
#     path("booking-success/<int:booking_id>/", views.booking_success, name="booking-success"),

#     # ---------- Favourites ----------
#     path('favourite/<int:club_id>/toggle/', views.toggle_favourite, name='toggle-favourite'),

#     # ---------- My Bookings ----------
#     path('my-bookings/', views.my_bookings, name='my-bookings'),
# ]

# # Serve media files
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# arena360/urls.py
from django.contrib import admin
from django.urls import path
from frontend import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Landing / dashboards
    # path('', views.home, name='home'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Auth
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_page, name='register'),

    # User dashboard (shows approved clubs)
    path('user-dashboard/', views.user_dashboard, name='user-dashboard'),

    # Partner (owner) flows
    path('partner-registration/', views.partner_register, name='partner-register'),  # add-club form
    path('partner-dashboard/', views.partner_dashboard, name='partner-dashboard'),
    path('partner-clubs/', views.partner_clubs, name='partner-clubs'),               # list of partner's clubs (simple)
    path('partner-bookings/', views.partner_bookings, name='partner-bookings'),      # partner's bookings
    path('add-club/', views.add_club, name='add-club'),                              # optional alias for partner register/add
    path('edit-club/<int:club_id>/', views.edit_club, name='edit-club'),

    # Profile
    # path('profile/', views.edit_profile, name='edit-profile'),
    path("edit-profile/", views.edit_profile, name="edit-profile"),



    # Favourites
    path('favourites/', views.favourites, name='favourites'),
    path('favourite/<int:club_id>/', views.toggle_favourite, name='toggle-favourite'),

    # Bookings / booking management
    path('my-bookings/', views.my_bookings, name='my-bookings'),
    path('booking-confirmation/', views.booking_confirmation, name='booking-confirmation'),

    # Club detail + booking flow
    path('club/<int:club_id>/', views.club_details, name='club-details'),
    # path('club/<int:club_id>/book/', views.book_slot, name='club-booking'),         # show sports + date -> slots
    path('club/<int:club_id>/book/', views.club_booking, name='club-booking'),
    path('club/<int:club_id>/book/confirm/', views.confirm_booking, name='confirm-booking'),
    path('club/<int:club_id>/book/submit/', views.submit_booking, name='submit_booking'),  # final POST to create booking

    path("help/", views.help_support, name="help-support"),

    # Payment
    path("payment/callback/", views.payment_callback, name="payment-callback"),

    # (Optional) helper / API endpoints can be added later (e.g. AJAX)
]

# Serve uploaded media files in DEBUG (club_image etc)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

