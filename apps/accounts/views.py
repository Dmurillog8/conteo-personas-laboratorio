from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegisterForm


def register(request):
    """Crea una cuenta y deja la sesión iniciada."""
    if request.user.is_authenticated:
        return redirect("monitoring:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"¡Bienvenido, {user.first_name or user.username}! Tu cuenta fue creada correctamente.",
            )
            return redirect("monitoring:dashboard")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})
