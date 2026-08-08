from django.http import HttpResponse
from django.shortcuts import render


async def health_check(request):
    return HttpResponse('OK', status=200)

