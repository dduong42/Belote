import itertools
import random
from enum import Enum
from typing import Dict, Generator, Iterable, List


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


class Card:
    def __init__(self, rank: Rank, suit: Suit) -> None:
        self.rank = rank
        self.suit = suit

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


class Player:
    def __init__(self):
        self.previous: Player = None
        self.next: Player = None
        self.hand: List[Card] = []

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

    def iter_from_next(self) -> Generator['Player', None, None]:
        player = self.next
        while True:
            yield player
            if player == self:
                break
            player = player.next


class Belote:
    def __init__(self, players: List[Player]) -> None:
        assert len(players) == 4

        self.players = players
        initialize_double_linked_list(players)
        self.deck = Deck()

    def start(self, dealer=None) -> None:
        # Get a random dealer
        dealer = dealer or random.choice(self.players)
        dealer.deal_5_cards(self.deck)

        card = self.deck.peek()
        print('Do you want to take this card?', card)
        for player in dealer.iter_from_next():
            if input() == 'yes':
                bidder = player
                trump = card.suit
                break
        else:
            print('What should be the trump?')
            choices = [suit.value for suit in Suit if suit != Suit(card.suit)]
            print(f'Choices: {" ".join(choices)}')
            for player in dealer.iter_from_next():
                suit = input()
                if suit in choices:
                    bidder = player
                    trump = Suit(suit)
                    break
            else:
                # Current player needs to cut and we need to start a new game.
                # We'll deal with that later
                return
        dealer.deal_remaining(self.deck, bidder)


def initialize_double_linked_list(players: List[Player]) -> None:
    assert len(players) == 4

    previous_player = players[-1]
    for player in players:
        previous_player.next = player
        player.previous = previous_player
        previous_player = player
