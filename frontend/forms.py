from django import forms
from .models import SportsClub, Sport,UserProfile
from django.contrib.auth.models import User

class SportsClubForm(forms.ModelForm):
    sports = forms.ModelMultipleChoiceField(
        queryset=Sport.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = SportsClub
        fields = [
            'club_name','location','available_courts','price_per_hour',
            'contact_number','open_time','close_time','club_image','sports'
        ]
        widgets = {
            'open_time': forms.TimeInput(attrs={'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'type': 'time'}),
        }

# class ProfileEditForm(forms.ModelForm):
#     class Meta:
#         model = User
#         fields = ['first_name', 'email']

class ProfileEditForm(forms.ModelForm):
    phone = forms.CharField(required=False, max_length=30, label="Phone Number")

    class Meta:
        model = User
        fields = ['first_name', 'email']  # username unchanged here

    def __init__(self, *args, **kwargs):
        # Accept profile instance via kwargs if provided
        profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if profile:
            self.fields['phone'].initial = profile.phone

    def save(self, commit=True):
        user = super().save(commit)
        phone = self.cleaned_data.get('phone', '')
        # ensure profile exists
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = phone
        if commit:
            profile.save()
        return user

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    is_partner = forms.BooleanField(required=False, label="Register as Partner")

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                is_partner=self.cleaned_data["is_partner"]
            )
        return user
