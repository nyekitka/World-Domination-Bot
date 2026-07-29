from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse
from django.template import loader

from database.clients import GameClient

async def render_stats(request: HttpRequest, game_id: int, round: int) -> HttpResponse:
    session = request.db_session
    game_client = GameClient()

    stats = await game_client.get_round_info(session, game_id, round)

    if stats is None:
        return HttpResponse('Игра или раунд не найдены', status=404)

    dumped_stats = stats.model_dump()
    template = await sync_to_async(loader.get_template)('statsview/index.html')

    max_development = 0
    for planet in dumped_stats['planets']:
        max_development = max(max_development, planet['development'])
    for planet in dumped_stats['planets']:
        planet['bar_height'] = planet['development'] / max_development * 100 if max_development != 0 else 5
    
    return HttpResponse(template.render(dumped_stats, request))
