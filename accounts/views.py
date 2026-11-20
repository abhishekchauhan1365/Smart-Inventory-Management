from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import UserLoginForm, StaffCreationForm, UserProfileUpdateForm
from .decorators import admin_required

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active or not user.is_active_staff:
                messages.error(request, "This account is inactive. Please contact the Pharmacy Administrator.")
                return render(request, 'accounts/login.html', {'form': form})
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please verify credentials.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileUpdateForm(request.POST, instance=user)
            pwd_form = PasswordChangeForm(user=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile details have been updated.")
                return redirect('profile')
            else:
                messages.error(request, "Please correct the errors in your profile form.")
        elif 'change_password' in request.POST:
            pwd_form = PasswordChangeForm(user=user, data=request.POST)
            profile_form = UserProfileUpdateForm(instance=user)
            if pwd_form.is_valid():
                user_updated = pwd_form.save()
                update_session_auth_hash(request, user_updated)
                messages.success(request, "Your password has been changed successfully.")
                return redirect('profile')
            else:
                messages.error(request, "Please correct the password errors below.")
    else:
        profile_form = UserProfileUpdateForm(instance=user)
        pwd_form = PasswordChangeForm(user=user)

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'pwd_form': pwd_form,
        'user_obj': user,
    })


@admin_required
def staff_list_view(request):
    staff_members = User.objects.all().order_by('-date_joined')
    return render(request, 'accounts/staff_list.html', {
        'staff_members': staff_members
    })


@admin_required
def staff_create_view(request):
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Staff account for '{user.username}' created successfully.")
            return redirect('staff_list')
        else:
            messages.error(request, "Could not create staff account. Please inspect the errors below.")
    else:
        form = StaffCreationForm()

    return render(request, 'accounts/staff_form.html', {
        'form': form,
        'title': 'Add New Pharmacy Staff Member',
    })


@admin_required
def staff_toggle_active_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot deactivate your own administrative account.")
        return redirect('staff_list')

    user.is_active_staff = not user.is_active_staff
    user.is_active = user.is_active_staff
    user.save()
    status_label = "activated" if user.is_active_staff else "deactivated"
    messages.success(request, f"User '{user.username}' has been {status_label}.")
    return redirect('staff_list')


@admin_required
def staff_delete_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete your own administrative account.")
        return redirect('staff_list')

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User account '{username}' has been deleted permanently.")
        return redirect('staff_list')

    return render(request, 'accounts/staff_confirm_delete.html', {'staff_user': user})
