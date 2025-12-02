from django.contrib import admin
from django.urls import path
from frontend.views import dashboard
from frontend import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
     path('club/<int:club_id>/book/', views.club_booking_page, name='club-book'),
    path('club/<int:club_id>/lock/', views.lock_slot, name='lock-slot'),           # AJAX: reserve / lock
    path('booking/<int:booking_id>/confirm/', views.confirm_booking, name='confirm-booking'),  # confirm after payment
    path('my-bookings/', views.my_bookings, name='my-bookings'),  # show bookings list
]
