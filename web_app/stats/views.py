from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader

from database.clients import GameClient
from database.clients.user import UserClient


async def custom_403_view(request):
    return render(request, 'stats/forbidden.html', status=403)

async def round_stats_page(request, game_id: int, round_num: int):
    return render(
        request,
        'stats/index.html',
        {'game_id': game_id, 'round_num': round_num},
    )

async def get_round_stats_api(request: HttpRequest, game_id: int, round_num: int) -> HttpResponse:
    session = request.db_session
    user = request.telegram_user

    game_client = GameClient()
    user_client = UserClient()

    is_admin = await user_client.is_user_admin(session, user['id'])
    if not is_admin:
        forb_template = await sync_to_async(loader.get_template)('app/forbidden.html')
        return HttpResponse(forb_template.render(request=request), code=403)


    stats = await game_client.get_round_info(session, game_id, round_num)

    if stats is None:
        return HttpResponse('Игра или раунд не найдены', status=404)

    dumped_stats = stats.model_dump()

    max_development = 0
    info = dumped_stats['info']
    info['anomaly_level'] = 100 - info['eco_rate']
    for planet in info['planets_data']:
        max_development = max(max_development, planet['rate_of_life'])
    for planet in info['planets_data']:
        planet['bar_height'] = (
            planet['rate_of_life'] / max_development * 100 if max_development != 0 else 5
        )

    return JsonResponse(info)
