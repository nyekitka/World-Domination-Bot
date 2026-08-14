import logging

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader

from database.clients import GameClient
from database.clients.user import UserClient


async def get_round_stats(request: HttpRequest, game_id: int, round_num: int) -> HttpResponse:
    forb_template = await sync_to_async(loader.get_template)('stats/forbidden.html')
    forb_response = HttpResponse(forb_template.render(request=request), status=403)

    if not hasattr(request, 'user_id') or request.user_id is None:
        return forb_response

    session = request.db_session
    user_id = request.user_id

    game_client = GameClient()
    user_client = UserClient()

    is_admin = await user_client.is_user_admin(session, user_id)
    if not is_admin:
        return forb_response

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

    return render(request, 'stats/index.html', info)
