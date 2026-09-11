from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, PatientProfile, DoctorProfile, StaffProfile


class RegistrationForm(UserCreationForm):
    """Public self-registration — PATIENT ONLY. Role is locked to PATIENT."""
    first_name = forms.CharField(max_length=30, required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'First name'}))
    last_name  = forms.CharField(max_length=30, required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'Last name'}))
    email      = forms.EmailField(required=False,
                                  widget=forms.EmailInput(attrs={'placeholder': 'Email (optional)'}))

    class Meta(UserCreationForm.Meta):
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'date_of_birth', 'gender')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_PATIENT          # Always PATIENT — never allow self-upgrade
        if commit:
            user.save()
            PatientProfile.objects.create(user=user)
        return user


class LoginForm(AuthenticationForm):
    pass


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'date_of_birth', 'gender', 'address')


# ─────────────────────────────────────────────────────────────
# ADMIN-ONLY FORMS — Doctor/Staff/Patient account management
# ─────────────────────────────────────────────────────────────

class AdminUserForm(forms.ModelForm):
    """Edit basic user fields (no password change)."""
    class Meta:
        model  = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'is_active')


class CreateDoctorForm(forms.ModelForm):
    """
    Admin-only form to create a Doctor account + DoctorProfile.
    Role is forcibly set to DOCTOR on save.
    """
    first_name           = forms.CharField(max_length=30, label='First Name')
    last_name            = forms.CharField(max_length=30, label='Last Name')
    email                = forms.EmailField(required=False, label='Email')
    phone                = forms.CharField(max_length=20, required=False, label='Phone')
    password             = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Password',
        validators=[validate_password],
    )
    password_confirm     = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Confirm Password',
    )
    is_active            = forms.ChoiceField(
        choices=[('True', 'Active'), ('False', 'Inactive')],
        initial='True',
        label='Account Status',
    )

    # DoctorProfile fields
    specialization       = forms.CharField(max_length=100, required=False, label='Specialization')
    license_number       = forms.CharField(max_length=50,  required=False, label='Medical Registration No.')
    department           = forms.CharField(max_length=100, required=False, label='Department')
    experience_years     = forms.IntegerField(min_value=0, required=False, initial=0, label='Years of Experience')

    class Meta:
        model  = User
        fields = ('username',)

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('password')
        pw2 = cleaned.get('password_confirm')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned

    def clean_is_active(self):
        return self.cleaned_data['is_active'] == 'True'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role       = User.ROLE_DOCTOR
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        user.email      = self.cleaned_data.get('email', '')
        user.phone      = self.cleaned_data.get('phone', '')
        user.is_active  = self.cleaned_data['is_active']
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            DoctorProfile.objects.create(
                user             = user,
                specialization   = self.cleaned_data.get('specialization', ''),
                license_number   = self.cleaned_data.get('license_number', ''),
                department       = self.cleaned_data.get('department', ''),
                experience_years = self.cleaned_data.get('experience_years') or 0,
            )
        return user


STAFF_TYPE_CHOICES = [
    ('',           '--- Select Staff Type ---'),
    ('LAB',        'Laboratory Staff'),
    ('NURSING',    'Nursing Staff'),
    ('RECEPTION',  'Reception Staff'),
    ('RECORDS',    'Medical Records Staff'),
    ('OTHER',      'Other'),
]


class CreateStaffForm(forms.ModelForm):
    """
    Admin-only form to create a Staff account + StaffProfile.
    Role is forcibly set to STAFF on save.
    """
    first_name       = forms.CharField(max_length=30, label='First Name')
    last_name        = forms.CharField(max_length=30, label='Last Name')
    email            = forms.EmailField(required=False, label='Email')
    phone            = forms.CharField(max_length=20, required=False, label='Phone')
    password         = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Password',
        validators=[validate_password],
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Confirm Password',
    )
    is_active        = forms.ChoiceField(
        choices=[('True', 'Active'), ('False', 'Inactive')],
        initial='True',
        label='Account Status',
    )

    # StaffProfile fields
    staff_type       = forms.ChoiceField(choices=STAFF_TYPE_CHOICES, required=False, label='Staff Type')
    department       = forms.CharField(max_length=100, required=False, label='Department')
    employee_id      = forms.CharField(max_length=50,  required=False, label='Employee ID')

    class Meta:
        model  = User
        fields = ('username',)

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('password')
        pw2 = cleaned.get('password_confirm')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned

    def clean_is_active(self):
        return self.cleaned_data['is_active'] == 'True'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role       = User.ROLE_STAFF
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        user.email      = self.cleaned_data.get('email', '')
        user.phone      = self.cleaned_data.get('phone', '')
        user.is_active  = self.cleaned_data['is_active']
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            StaffProfile.objects.get_or_create(
                user       = user,
                defaults   = {
                    'department':  self.cleaned_data.get('department', ''),
                    'employee_id': self.cleaned_data.get('employee_id', ''),
                }
            )
        return user


class ResetPasswordForm(forms.Form):
    """Admin resets another user's password."""
    new_password     = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='New Password',
        validators=[validate_password],
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        label='Confirm Password',
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned
