from unittest import TestCase

from belote import Player, initialize_double_linked_list


class InitializeDoubleLinkedList(TestCase):
    def test_initialize_double_linked_list(self):
        player_1 = Player()
        player_2 = Player()
        player_3 = Player()
        player_4 = Player()

        initialize_double_linked_list(
            [player_1, player_2, player_3, player_4])
        self.assertEqual(player_1.next, player_2)
        self.assertEqual(player_1.previous, player_4)

        self.assertEqual(player_2.next, player_3)
        self.assertEqual(player_2.previous, player_1)

        self.assertEqual(player_3.next, player_4)
        self.assertEqual(player_3.previous, player_2)

        self.assertEqual(player_4.next, player_1)
        self.assertEqual(player_4.previous, player_3)
