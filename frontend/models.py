from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime, timedelta, time
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} profile"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)

class Sport(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Sport"
        verbose_name_plural = "Sports"

    def __str__(self):
        return self.name

class SportsClub(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clubs')
    club_name = models.CharField(max_length=150)
    location = models.CharField(max_length=255, blank=True)
    available_courts = models.PositiveIntegerField(default=1)
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    contact_number = models.CharField(max_length=20, blank=True)
    open_time = models.TimeField(default="06:00:00")
    close_time = models.TimeField(default="23:00:00")
    club_image = models.ImageField(upload_to='club_images/', blank=True, null=True)
    sports = models.ManyToManyField(Sport, blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    slot_duration = models.DurationField(default=timedelta(minutes=60))

    def __str__(self):
        return self.club_name

    def generate_slots_for_date(self, date):
        slots = []
        start_dt = datetime.combine(date, self.open_time)
        end_dt = datetime.combine(date, self.close_time)
        cur = start_dt
        while cur + self.slot_duration <= end_dt:
            slots.append((cur.time(), (cur + self.slot_duration).time()))
            cur += self.slot_duration
        return slots

class Favourite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(SportsClub, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'club')

# class Booking(models.Model):
#     STATUS_CHOICES = [
#         ('reserved', 'Reserved'),
#         ('confirmed', 'Confirmed'),
#         ('cancelled', 'Cancelled'),
#     ]

#     user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='bookings')
#     client_name = models.CharField(max_length=150, blank=True, null=True)
#     phone = models.CharField(max_length=30, blank=True, null=True)
#     club = models.ForeignKey(SportsClub, on_delete=models.CASCADE, related_name='bookings')
#     sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
#     date = models.DateField()
#     start_time = models.TimeField()
#     end_time = models.TimeField()
#     amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reserved')
#     reserved_until = models.DateTimeField(blank=True, null=True)
#     razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
#     razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ('club', 'sport', 'date', 'start_time')

#     def __str__(self):
#         return f"{self.club} - {self.sport} - {self.date} {self.start_time}"

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(SportsClub, on_delete=models.CASCADE)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.club.club_name} | {self.sport.name} | {self.date}"
