import os
from game_classes import Game


def html_page_generator(game: Game):
    os.chdir("round results")
    file = open(f'results_{game.id}_{game.show_round()}.html', 'w', encoding='UTF-8')
    with open('presets/head.txt', encoding='UTF-8') as head:
        file.write(''.join(head.readlines()).format(game.id))
    i = 1
    planets = game.planets()
    for planet in planets:
        cities = planet.cities(False)
        names_of_cities = [c.name() for c in cities]
        percentages = [c.rate_of_life() for c in cities]
        s = None
        with open('presets/planet panel.txt', encoding='UTF-8') as panel:
            s = ''.join(panel.readlines())
            args = [planet.name(), i]
            for j in range(len(names_of_cities)):
                args.extend(
                    ['', names_of_cities[j]] if percentages[j] != 0 else ['dead-', f'<s>{names_of_cities[j]}</s>'])
            for j in range(len(names_of_cities)):
                args.extend(['dead-' if percentages[j] == 0 else '', percentages[j]])
            s = s.format(*args)
            file.write(s)
        i += 1
    with open('presets/chart begin preset.txt', encoding='UTF-8') as chart:
        file.write(''.join(chart.readlines()))
    rates_of_life = [planet.rate_of_life() for planet in planets]
    max_rate = max(rates_of_life)
    bar_preset = None
    with open('presets/bar preset.txt', encoding='UTF-8') as bar:
        bar_preset = ''.join(bar.readlines())
    for j in range(len(planets)):
        file.write(bar_preset.format(rates_of_life[j] * 100 / max_rate, rates_of_life[j], planets[j].name()))
    with open('presets/ending preset.txt', encoding='UTF-8') as end:
        file.write(''.join(end.readlines()).format(100 - game.eco_rate()))
    file.close()
    os.chdir("..")

def css_generator(game: Game):
    gameid = game.id
    n = game.number_of_planets()
    colors = ('green', 'red', 'blue', 'orange', 'purple', 'yellowgreen', 'darkred', 'darkblue')
    os.chdir("round results")
    file = open(f'style{gameid}.css', 'w', encoding='UTF-8')
    preset = open(f'presets/style.css', 'r', encoding='UTF-8')
    file.write(''.join(preset.readlines()))
    preset.close()
    file.write('.panel-1')
    for i in range(2, n + 1):
        file.write(f', .panel-{i}')
    with open('presets/panel settings.txt') as sets:
        file.write(''.join(sets.readlines()))
    file.write('.upper-half-1')
    for i in range(2, n + 1):
        file.write(f', .upper-half-{i}')
    with open('presets/upper-half settings.txt') as sets:
        file.write(''.join(sets.readlines()))
    for i in range(n):
        file.write(f""".upper-half-{i + 1} {{
    background-color: {colors[i]};
}}\n\n""")
    file.close()
    os.chdir("..")