# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import url_for
from flask.ext.testing import TestCase as FlaskTestCase

from bolao.main import app_factory
from bolao.database import db
from bolao.models import Game, Team, User


class TestCase(FlaskTestCase):

    def assertFlashes(self, message, category='message'):
        return self.assert_flashes(message, category)

    def assert_flashes(self, message, category='message'):

        with self.client.session_transaction() as session:

            message = message.encode('utf-8')
            try:
                final_category, final_message = session['_flashes'][0]
                final_message = final_message.encode('utf-8')
            except KeyError:
                raise AssertionError('Nothing flashed')

            self.assertEqual(message, final_message)
            self.assertEqual(category, final_category)


class GamesTest(TestCase):

    def create_app(self):
        app = app_factory('Testing')
        return app

    def setUp(self):
        db.create_all()
        self.user = User(name="Test", email="email@test.co", active=True)
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_games(self):

        bra = Team(name="Brasil", alias="BRA")
        usa = Team(name="United States", alias="USA")
        now = datetime.now() + timedelta(days=1)
        game = Game(team1=bra, team2=usa, time=now)
        db.session.add(bra)
        db.session.add(usa)
        db.session.add(game)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        response = self.client.get("/jogos")
        self.assert200(response)
        self.assertIn('BRA', response.data)
        self.assertIn('USA', response.data)
        self.assertIn('apostar', response.data)
#        self.assert_template_used('games.html')

    def test_view_games_after_limit(self):
        bra = Team(name="Brasil", alias="BRA")
        usa = Team(name="United States", alias="USA")
        now = datetime.now() + timedelta(days=-1)
        game = Game(team1=bra, team2=usa, time=now)
        db.session.add(bra)
        db.session.add(usa)
        db.session.add(game)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        response = self.client.get(url_for('.games'))
        self.assertIn('expirou', response.data)

    def test_bet_game_view_after_limit(self):
        bra = Team(name="Brasil", alias="BRA")
        usa = Team(name="United States", alias="USA")
        now = datetime.now() + timedelta(days=-1)
        game = Game(team1=bra, team2=usa, time=now)
        db.session.add(bra)
        db.session.add(usa)
        db.session.add(game)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id

        response = self.client.get(url_for('.bet_game_view', game_id=game.id))
        self.assertRedirects(response, url_for('.games'))
        expected_message = u"O prazo para apostar em <strong>%s</strong> expirou." % game
        self.assert_flashes(expected_message, category='warning')

    def test_bet_games_with_inactive_user(self):

        from bolao.views import INACTIVE_USER_MESSAGE

        bra = Team(name="Brasil", alias="BRA")
        usa = Team(name="United States", alias="USA")
        now = datetime.now()
        game = Game(team1=bra, team2=usa, time=now)
        db.session.add(bra)
        db.session.add(usa)
        db.session.add(game)
        db.session.commit()

        user = User(name="Inactive", email="inactive@test.co", active=False)
        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id
        response = self.client.get(url_for('.bet_game_view', game_id=game.id))
        self.assertRedirects(response, url_for('.games'))
        self.assert_flashes(INACTIVE_USER_MESSAGE, category='warning')


class ChampionsTest(TestCase):

    def create_app(self):
        app = app_factory('Testing')
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_view_champions_limit(self):
        self.app.config['BOLAO_BET_CHAMPIONS_LIMIT'] = datetime(1990, 1, 1)
        response = self.client.get('/campeoes')
        self.assertRedirects(response, url_for('bolao.index'))
        self.assert_flashes("O prazo para escolher as primeiras colocadas expirou.", category='warning')

    def test_bet_champions_limit(self):
        data = {}
        self.app.config['BOLAO_BET_CHAMPIONS_LIMIT'] = datetime(1990, 1, 1)
        response = self.client.post('/campeoes', data=data)
        self.assertRedirects(response, url_for('bolao.index'))
        self.assert_flashes("O prazo para escolher as primeiras colocadas expirou.", category='warning')

    def test_champions_with_inactive_user(self):

        from bolao.views import INACTIVE_USER_MESSAGE

        user = User(name="Inactive", email="inactive@test.co", active=False)
        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id
        response = self.client.get('/campeoes')
        self.assertRedirects(response, url_for('bolao.index'))
        self.assert_flashes(INACTIVE_USER_MESSAGE, category='warning')


class ScorerTest(TestCase):

    def create_app(self):
        app = app_factory('Testing')
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_view_scorer_limit(self):
        self.app.config['BOLAO_BET_SCORER_LIMIT'] = datetime(1990, 1, 1)
        response = self.client.get('/artilheiros')
        self.assertRedirects(response, url_for('bolao.index'))
        self.assert_flashes("O prazo para escolher os artilheiros expirou.", category='warning')

    def test_bet_scorer_limit(self):
        data = {}
        self.app.config['BOLAO_BET_SCORER_LIMIT'] = datetime(1990, 1, 1)
        response = self.client.post('/artilheiros', data=data)
        self.assertRedirects(response, url_for('bolao.index'))
        self.assert_flashes("O prazo para escolher os artilheiros expirou.", category='warning')

    def test_scorer_with_inactive_user(self):

        from bolao.views import INACTIVE_USER_MESSAGE

        user = User(name="Inactive", email="inactive@test.co", active=False)
        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id
        response = self.client.get('/artilheiros')
        self.assertRedirects(response, url_for('bolao.index'))
        self.assert_flashes(INACTIVE_USER_MESSAGE, category='warning')
