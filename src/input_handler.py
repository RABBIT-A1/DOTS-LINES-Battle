# -*- coding: utf-8 -*-
"""鼠标与键盘事件到 UI、画线和页面导航指令的转换。"""

import pygame

from .geometry import vec_add


class InputHandler:
    @staticmethod
    def _button_at(buttons, position):
        for button in buttons:
            if button.enabled and button.contains(position):
                return button
        return None

    @staticmethod
    def _start_game(game):
        game.lerp_speed = game.renderer.slider.value
        game.audio.play("ui_click")
        game.start_game()

    @staticmethod
    def _open_rules(game):
        game.audio.play("ui_click")
        game.state = "RULES"

    @staticmethod
    def _return_title(game):
        game.audio.play("ui_click")
        game.state = "TITLE"
        game.mouse_held = False
        pygame.event.set_grab(False)
        game.ai_trail_plan = []

    def handle_events(self, game):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if (
                event.type == pygame.MOUSEMOTION
                and game.state == "DRAW"
                and game.current_player == game.p1
                and game.mouse_held
            ):
                game.last_mouse_target = event.pos
                if event.rel != (0, 0):
                    game.last_cursor_move_time = pygame.time.get_ticks()
                    game.pending_cursor_delta = vec_add(
                        game.pending_cursor_delta, event.rel
                    )

            if game.state == "TITLE":
                game.renderer.slider.handle_event(event)

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    if game.state == "RULES":
                        self._return_title(game)
                        continue
                    if game.state in ("DRAW", "GAME_OVER"):
                        self._return_title(game)
                        continue

                if game.state == "TITLE":
                    if event.key == pygame.K_r:
                        self._open_rules(game)
                        continue
                    if event.key in (
                        pygame.K_RETURN,
                        pygame.K_SPACE,
                    ):
                        self._start_game(game)
                    continue

                if game.state == "RULES":
                    if event.key in (
                        pygame.K_LEFT,
                        pygame.K_a,
                    ):
                        game.rules_section = (
                            game.rules_section - 1
                        ) % len(game.renderer.rules_tab_rects)
                        game.audio.play("ui_click")
                        continue
                    if event.key in (
                        pygame.K_RIGHT,
                        pygame.K_d,
                    ):
                        game.rules_section = (
                            game.rules_section + 1
                        ) % len(game.renderer.rules_tab_rects)
                        game.audio.play("ui_click")
                        continue
                    if event.key in (
                        pygame.K_RETURN,
                        pygame.K_SPACE,
                    ):
                        self._start_game(game)
                    continue

                if game.state == "GAME_OVER":
                    if event.key in (
                        pygame.K_RETURN,
                        pygame.K_SPACE,
                    ):
                        game.audio.play("ui_click")
                        game.start_game()
                    continue

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                if game.state == "TITLE":
                    if game.renderer.slider.rect.collidepoint(
                        event.pos
                    ):
                        continue
                    button = self._button_at(
                        game.renderer.title_buttons, event.pos
                    )
                    if button is None:
                        continue
                    if button.action == "start":
                        self._start_game(game)
                    elif button.action == "rules":
                        self._open_rules(game)
                    continue

                if game.state == "RULES":
                    tab_clicked = False
                    for index, rect in enumerate(
                        game.renderer.rules_tab_rects
                    ):
                        if rect.collidepoint(event.pos):
                            game.rules_section = index
                            game.audio.play("ui_click")
                            tab_clicked = True
                            break
                    if tab_clicked:
                        continue
                    button = self._button_at(
                        game.renderer.rules_buttons, event.pos
                    )
                    if button is None:
                        continue
                    if button.action == "start":
                        self._start_game(game)
                    elif button.action == "back":
                        self._return_title(game)
                    continue

                if game.state == "GAME_OVER":
                    button = self._button_at(
                        game.renderer.game_over_buttons, event.pos
                    )
                    if button is None:
                        continue
                    game.audio.play("ui_click")
                    if button.action == "restart":
                        game.start_game()
                    elif button.action == "menu":
                        self._return_title(game)
                    continue

                if (
                    game.state == "DRAW"
                    and game.current_player == game.p1
                ):
                    game.mouse_held = True
                    game.turn_start_pos = game.current_player.dot_pos
                    game.last_mouse_target = event.pos
                    game.last_cursor_move_time = pygame.time.get_ticks()
                    game.pending_cursor_delta = (0, 0)
                    pygame.event.set_grab(True)
                    game.audio.play("draw_start")

            if (
                event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
            ):
                if (
                    game.state == "DRAW"
                    and game.current_player == game.p1
                    and game.mouse_held
                ):
                    game.mouse_held = False
                    game.end_draw_phase()

        return True
