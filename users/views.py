from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache


@login_required
@never_cache
def dashboard(request):
    return render(request, "dashboard.html")
