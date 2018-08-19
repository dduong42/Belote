import asyncio
import itertools
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Generator, Iterable, List, Optional, Tuple


class Rank(Enum):
    ACE = 'A'
    KING = 'K'
    QUEEN = 'Q'
    JACK = 'J'
    TEN = '10'
    NINE = '9'
    EIGHT = '8'
    SEVEN = '7'


TRUMP_ORDER: Dict[Rank, int] = {
    Rank.SEVEN: 0,
    Rank.EIGHT: 1,
    Rank.QUEEN: 2,
    Rank.KING: 3,
    Rank.TEN: 4,
    Rank.ACE: 5,
    Rank.NINE: 6,
    Rank.JACK: 7,
}
NORMAL_ORDER: Dict[Rank, int] = {
    Rank.SEVEN: 0,
    Rank.EIGHT: 1,
    Rank.NINE: 2,
    Rank.JACK: 3,
    Rank.QUEEN: 4,
    Rank.KING: 5,
    Rank.TEN: 6,
    Rank.ACE: 7,
}
TRUMP_VALUE: Dict[Rank, int] = {
    Rank.SEVEN: 0,
    Rank.EIGHT: 0,
    Rank.QUEEN: 3,
    Rank.KING: 4,
    Rank.TEN: 10,
    Rank.ACE: 11,
    Rank.NINE: 14,
    Rank.JACK: 20,
}
NORMAL_VALUE: Dict[Rank, int] = {
    Rank.SEVEN: 0,
    Rank.EIGHT: 0,
    Rank.NINE: 0,
    Rank.JACK: 2,
    Rank.QUEEN: 3,
    Rank.KING: 4,
    Rank.TEN: 10,
    Rank.ACE: 11,
}


class Suit(Enum):
    DIAMOND = '♦'
    HEARTS = '♥'
    SPADES = '♠'
    CLUBS = '♣'


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def get_value(self, trump: Suit) -> int:
        if self.suit == trump:
            return TRUMP_VALUE[self.rank]
        else:
            return NORMAL_VALUE[self.rank]

    def get_rank(self, trump: Suit) -> int:
        if self.suit == trump:
            return TRUMP_ORDER[self.rank]
        else:
            return NORMAL_ORDER[self.rank]

    @classmethod
    def from_string(cls, s: str):
        if len(s) < 2:
            raise ValueError(f'{s} is not a valid card.')
        try:
            return cls(Rank(s[:-1]), Suit(s[-1]))
        except ValueError:
            raise ValueError(f'{s} is not a valid card.')

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'<{cls_name}: {self.rank.value}{self.suit.value}>'


class Deck:
    def __init__(self):
        self.cards: List[Card] = [
            Card(rank, suit)
            for rank, suit in itertools.product(Rank, Suit)
        ]
        # There should be 32 cards
        assert len(self.cards) == 32
        random.shuffle(self.cards)

    def cut(self, index: int) -> None:
        assert 0 <= index < len(self.cards)

        first_chunk = self.cards[:index]
        second_chunk = self.cards[index:]

        # We should cut at least 3 cards
        assert len(first_chunk) >= 3
        assert len(second_chunk) >= 3

        self.cards = second_chunk + first_chunk

    def pop_many(self, nb_cards: int) -> List[Card]:
        cards = [self.cards.pop() for _ in range(nb_cards)]

        assert len(cards) == nb_cards
        return cards

    def peek(self) -> Card:
        return self.cards[-1]

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'<{cls_name}: {repr(self.cards)}>'


@dataclass
class Team:
    score: int = 0
    has_contract: bool = False


@dataclass
class Trick:
    game: 'Belote'
    pile: List[Tuple['Player', Card]] = field(default_factory=list)

    def pile_key_function(self, player_card: Tuple['Player', Card]) -> Tuple[int, int]:
        _, card = player_card
        if card.suit == self.game.trump:
            return 2, card.get_rank(self.game.trump)
        elif card.suit == self.dominant_suit:
            return 1, card.get_rank(self.game.trump)
        else:
            return 0, card.get_rank(self.game.trump)

    @property
    def dominant_suit(self) -> Optional[Suit]:
        try:
            _, first_card = self.pile[0]
        except IndexError:
            return None
        return first_card.suit

    @property
    def winning_player_card(self) -> Tuple['Player', Card]:
        return max(self.pile, key=self.pile_key_function)

    @property
    def total_score(self):
        return sum((card.get_value(self.game.trump) for _, card in self.pile))


class Player:
    def __init__(self, transport: asyncio.WriteTransport):
        self.previous: Player = None
        self.next: Player = None
        self.hand: List[Card] = []
        self.team: Team = None
        self.number: int
        self.transport = transport
        self.queue = asyncio.Queue()

    def send_hand(self):
        self.send_message(f'Your hand is {self.hand}')

    def set_number(self, number: int):
        self.number = number
        self.send_message(f'You are the Player {number}')

    def send_message(self, msg: str):
        """Send a message to the player."""
        msg += '\n'
        self.transport.write(msg.encode())

    async def recv_message(self):
        """Get a message from the player."""
        return await self.queue.get()

    def plays(self, trick: Trick, card: Card):
        trick.pile.append((self, card))
        self.hand.remove(card)
        for player in self.iter_from_next():
            player.send_message(f'Player {self.number} is playing {card}')

    def add_to_hand(self, cards: Iterable[Card]) -> None:
        self.hand.extend(cards)

    def deal_5_cards(self, deck: Deck) -> None:
        # Deal 2 cards, then 3 cards, starting from the next player
        for player in self.iter_from_next():
            player.add_to_hand(deck.pop_many(2))

        for player in self.iter_from_next():
            player.add_to_hand(deck.pop_many(3))

    def deal_remaining(self, deck: Deck, bidder: 'Player') -> None:
        # Bidder gets the top card
        bidder.add_to_hand(deck.pop_many(1))

        # Deal the rest of the cards. Starting from the next player.
        # Bidder gets 2 cards, the other people get 3 cards.
        for player in self.iter_from_next():
            nb_cards = 2 if player == bidder else 3
            player.add_to_hand(deck.pop_many(nb_cards))

    def iter_from_self(self) -> Generator['Player', None, None]:
        yield from self.previous.iter_from_next()

    def iter_from_next(self) -> Generator['Player', None, None]:
        player = self.next
        while True:
            yield player
            if player == self:
                break
            player = player.next

    def legal_moves(self, trick: Trick) -> List[Card]:
        if not trick.dominant_suit:
            return self.hand
        winning_player, winning_card = trick.winning_player_card
        same_suit = [card for card in self.hand
                     if card.suit == trick.dominant_suit]
        if trick.dominant_suit == trick.game.trump:
            if not same_suit:
                return self.hand
            if winning_player == self.team:
                return same_suit
            higher_trumps = [card for card in same_suit
                             if card.get_rank(trick.game.trump) > winning_card.get_rank(trick.game.trump)]
            return higher_trumps or same_suit

        if same_suit:
            return same_suit
        trumps = [card for card in self.hand
                  if card.suit == trick.game.trump]
        if trumps:
            if winning_player == self.team:
                return trumps
            higher_trumps = [card for card in same_suit
                             if card.get_rank(trick.game.trump) > winning_card.get_rank(trick.game.trump)]
            return higher_trumps or trumps
        # At this point, you can play whatever you want.
        return self.hand

    async def ask_to_play(self, trick: Trick):
        legal_moves = self.legal_moves(trick)
        self.send_message(f'What are you playing? {legal_moves}')
        # TODO: Handle errors
        card = Card.from_string(await self.recv_message())
        assert card in legal_moves
        self.plays(trick, card)


class Belote:
    def __init__(self) -> None:
        self.players: List[Player] = []
        self.deck = Deck()
        self.trump: Suit

    def set_teams(self):
        self.teams = [Team(), Team()]

        self.players[0].team = self.teams[0]
        self.players[2].team = self.teams[0]

        self.players[1].team = self.teams[1]
        self.players[3].team = self.teams[1]

    @property
    def bidding_team(self) -> Team:
        return next(team for team in self.teams if team.has_contract)

    @property
    def other_team(self) -> Team:
        return next(team for team in self.teams if not team.has_contract)

    def add_player(self, player: Player):
        self.players.append(player)
        player.set_number(self.players.index(player) + 1)

    def broadcast(self, msg):
        for player in self.players:
            player.send_message(msg)

    async def start(self, dealer=None) -> None:
        # Get a random dealer
        dealer = dealer or random.choice(self.players)
        self.broadcast(f'The dealer is Player {dealer.number}')
        dealer.deal_5_cards(self.deck)

        card = self.deck.peek()
        self.broadcast(f'The card is {card}')
        for player in self.players:
            player.send_hand()
        for player in dealer.iter_from_next():
            player.send_message('Do you want to take the card?')
            answer = await player.recv_message()
            if answer == 'yes':
                bidder = player
                self.trump = card.suit
                self.broadcast(f'Player {bidder.number} took the card')
                break
        else:
            choices = [suit.value for suit in Suit if suit != Suit(card.suit)]
            msg = f'What should be the trump?\nChoices: {" ".join(choices)}'
            for player in dealer.iter_from_next():
                player.send_message(msg)
                suit = await player.recv_message()
                if suit in choices:
                    bidder = player
                    self.trump = Suit(suit)
                    self.broadcast(f'Player {bidder.number} choosed {suit}')
                    break
            else:
                # Current player needs to cut and we need to start a new game.
                # We'll deal with that later
                return
        bidder.team.has_contract = True
        dealer.deal_remaining(self.deck, bidder)
        for player in self.players:
            player.send_hand()

        nb_tricks = 8
        winner = dealer.next
        for _ in range(nb_tricks):
            trick: Trick = Trick(self)
            for player in winner.iter_from_self():
                await player.ask_to_play(trick)

            winner, winning_card = trick.winning_player_card
            winner.team.score += trick.total_score
        # The winner of the last trick gets 10 points
        winner.team.score += 10
        print(f'Bidding team: {self.bidding_team.score}')
        print(f'Other team: {self.other_team.score}')
        if self.bidding_team.score > self.other_team.score:
            print('Bidding team won!')
        else:
            print('Other team won!')

    def start_game_if_ready(self, loop):
        if len(self.players) == 4:
            initialize_double_linked_list(self.players)
            self.set_teams()
            asyncio.ensure_future(self.start())


def initialize_double_linked_list(players: List[Player]) -> None:
    assert len(players) == 4

    previous_player = players[-1]
    for player in players:
        previous_player.next = player
        player.previous = previous_player
        previous_player = player


class BeloteProtocol(asyncio.Protocol):
    def __init__(self, game, loop):
        super().__init__()
        self.game = game
        self.loop = loop

    def connection_made(self, transport):
        self.player = Player(transport)
        self.game.add_player(self.player)
        self.game.start_game_if_ready(self.loop)

    def data_received(self, data):
        self.player.queue.put_nowait(data.decode().strip())


loop = asyncio.get_event_loop()
loop.set_debug(True)
belote = Belote()
server = loop.run_until_complete(
loop.create_server(lambda: BeloteProtocol(belote, loop), '127.0.0.1', 8888))

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
