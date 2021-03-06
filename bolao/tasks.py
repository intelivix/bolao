
from collections import Counter
from sqlalchemy import func, select, and_, or_
from sqlalchemy.orm.session import make_transient

from bolao.database import db
from bolao.models import User, Team, Scorer, BetGame, BetScorer, BetChampions

EXACT_RESULT = 18
RESULT_AND_A_SCORE = 12
ONLY_RESULT = 9
ONLY_ONE_SCORE = 3
SCORER_POINTS = 20
EXACT_CHAMPIONS = 10
CHAMPIONS_POINTS = 5


def update_scorer(scorer):

    # detach from the session to load the database instance to compare
    scorer_id = scorer.id
    make_transient(scorer)
    scorer.id = scorer_id
    scorer_db = Scorer.query.get(scorer_id)
    if scorer_db.scorer == scorer.scorer:
        return
    # reattach the instance
    scorer = db.session.merge(scorer)

    bets = BetScorer.query.filter(or_(BetScorer.scorer1==scorer, BetScorer.scorer2==scorer))

    for bet in bets:
        if not scorer.scorer and bet.score == 0:
            continue
        if scorer.scorer:
            bet.score += SCORER_POINTS
        else:
            bet.score -= SCORER_POINTS

        # pass as param since the user.bet_scorer backref is None here
        update_total_score(bet.user, bet_scorer=bet)

    db.session.commit()


def update_champions(first, second, third, fourth):

    assert None not in (first, second, third, fourth)

    # reset all
    BetChampions.query.update({'score': 0})
    Team.query.update({'position': 0})

    first.position = 1
    second.position = 2
    third.position = 3
    fourth.position = 4

    rank = (first.id, second.id, third.id, fourth.id)
    bets = BetChampions.query.filter(or_(
      BetChampions.first_id.in_(rank),
      BetChampions.second_id.in_(rank),
      BetChampions.third_id.in_(rank),
      BetChampions.fourth_id.in_(rank))).all()

    def update_pos(arg):
      bet_team, team = arg[0], arg[1]
      if bet_team.id in rank:
        return EXACT_CHAMPIONS if bet_team == team else CHAMPIONS_POINTS
      return 0

    def update_all(bet):
        bet.score = sum(map(update_pos, [(bet.first, first), (bet.second, second), (bet.third, third), (bet.fourth, fourth)]))
        update_total_score(bet.user, bet_champions=bet)

    map(update_all, bets)
    db.session.commit()


def update_total_score(user, bet_scorer=None, bet_champions=None):
    user.score_total = user.score_games
    bet_scorer = bet_scorer or user.bet_scorer
    if bet_scorer:
        user.score_total += bet_scorer.score
    bet_champions = bet_champions or user.bet_champions
    if bet_champions:
        user.score_total += bet_champions.score
    return user.score_total


def update_scores_by_game(game):

    bets = BetGame.query.filter_by(game=game)

    for bet in bets:
        if bet.score_team1 == game.score_team1 and bet.score_team2 == game.score_team2:
            bet.score = EXACT_RESULT
        elif (bet.score_team1 > bet.score_team2 and game.score_team1 > game.score_team2) or \
             (bet.score_team1 < bet.score_team2 and game.score_team1 < game.score_team2) or \
             (bet.score_team1 == bet.score_team2 and game.score_team1 == game.score_team2):
            bet.score = ONLY_RESULT
            if bet.score_team1 == game.score_team1 or bet.score_team2 == game.score_team2:
                bet.score = RESULT_AND_A_SCORE
        elif bet.score_team1 == game.score_team1 or bet.score_team2 == game.score_team2:
            bet.score = ONLY_ONE_SCORE
        else:
            bet.score = 0  # force update

    db.session.commit()


def update_ranking():
    for user in User.ranking():
        user.score_games = db.session.query(func.sum(BetGame.score)).filter_by(user=user).scalar() or 0
        update_ranking_criterias(user)
        update_total_score(user)
    db.session.commit()


def update_positions():
    """Update ranking positions."""
    for pos, user in enumerate(User.ranking()):
        user.last_pos = user.pos
        user.pos = pos + 1
    db.session.commit()


def update_ranking_criterias(user):
    criterias = compute_criterias(user)
    user.crit_exact = criterias.get('exact', 0)
    user.crit_game_result = criterias.get('game_result', 0)
    user.crit_win_goals = criterias.get('win_goals', 0)
    user.crit_lose_goals = criterias.get('lose_goals', 0)


def compute_criterias(user):

    criterias = Counter()
    bets = BetGame.query.filter_by(user=user)
    for bet in bets:
        if bet.score == EXACT_RESULT:
            criterias['exact'] += 1
            criterias['game_result'] += 1
        elif bet.score == RESULT_AND_A_SCORE or bet.score == ONLY_RESULT:
            criterias['game_result'] += 1

        # this criteria is not valid just for draw
        if bet.game.score_team1 != bet.game.score_team2:
            home_is_winner = bet.game.score_team1 > bet.game.score_team2
            if (home_is_winner and bet.score_team1 == bet.game.score_team1) or \
                  (not home_is_winner and bet.score_team2 == bet.game.score_team2):
                criterias['win_goals'] += 1
            # also scores for exact match
            if (home_is_winner and bet.score_team2 == bet.game.score_team2) or \
                  (not home_is_winner and bet.score_team1 == bet.game.score_team1):
                criterias['lose_goals'] += 1

    return criterias

