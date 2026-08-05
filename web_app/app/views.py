from django.http import HttpResponse


async def health_check(request):
    return HttpResponse('OK', status=200)
