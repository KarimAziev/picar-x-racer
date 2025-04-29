import random
from math import cos, pi, sin
from time import sleep
from typing import TYPE_CHECKING, List, Literal, Union

from .data_types import ActionAngles

if TYPE_CHECKING:
    from .pidog import Pidog


def scratch(robot_dog: "Pidog") -> None:
    """
    Command the robot dog to perform a “scratch” action.

    The routine first has the dog sit down and then moves the head to a
    scratching position. It then raises the front legs and repeatedly performs
    a leg-scratch motion before resetting the head and returning to a sitting pose.
    """
    head_reset_angles: List[ActionAngles] = [[0, 0, -40]]
    head_scratch_angles: List[ActionAngles] = [[30, 70, -10]]
    front_leg_raise_angles: List[ActionAngles] = [
        [
            30,
            60,
            50,
            50,
            80,
            -45,
            -80,
            38,
        ]  # Modified last servo value to improve stability
    ]
    leg_scratch_cycle: List[ActionAngles] = [
        [
            30,
            60,
            40,
            40,
            80,
            -45,
            -80,
            38,
        ],
        [30, 60, 50, 50, 80, -45, -80, 38],
    ]

    # Initiate sitting posture and adjust head for scratching.
    robot_dog.do_action("sit", speed=80)
    robot_dog.head_move(head_scratch_angles, immediately=False, speed=80)
    robot_dog.legs_move(front_leg_raise_angles, immediately=False, speed=80)
    robot_dog.wait_all_done()

    # Perform the scratching motion repeatedly.
    for _ in range(10):
        robot_dog.legs_move(leg_scratch_cycle, immediately=False, speed=94)
        robot_dog.wait_all_done()

    # Return head to the default position and have the dog sit.
    robot_dog.head_move(head_reset_angles, immediately=False, speed=80)
    robot_dog.do_action("sit", speed=80)
    robot_dog.wait_all_done()


# Note 1: Last servo(4th legs) original value is 45, change to 40 to push down
# alittle bit to support the rasing legs, prevent the dog from falling down.


def handshake(robot_dog: "Pidog") -> None:
    """
    Command the robot dog to perform a “handshake” action.

    The sequence raises a leg, executes repeated handshake motions,
    withdraws the leg, then gradually lowers the hand while also moving the head.
    """
    front_leg_raise_angles: List[ActionAngles] = [
        [30, 60, -20, 65, 80, -45, -80, 38]  # Angles for raising the leg for handshake.
    ]
    handshake_motion_angles: List[ActionAngles] = [
        [30, 60, 10, -25, 80, -45, -80, 38],
        [30, 60, 10, -35, 80, -45, -80, 38],
    ]
    leg_withdraw_angles: List[ActionAngles] = [[30, 60, -40, 30, 80, -45, -80, 38]]

    # Raise the leg and wait for the movement to complete.
    robot_dog.legs_move(front_leg_raise_angles, immediately=False, speed=80)
    robot_dog.wait_all_done()
    sleep(0.1)

    # Repeat the handshake motion several times.
    for _ in range(8):
        robot_dog.legs_move(handshake_motion_angles, immediately=False, speed=90)
        robot_dog.wait_all_done()

    # Withdraw the leg after handshake.
    robot_dog.legs_move(leg_withdraw_angles, immediately=False, speed=80)

    # Gradually lower the hand.
    hand_lowering_angles: List[ActionAngles] = [
        [30, 60, -30, -40, 80, -45, -80, 45],
        [30, 60, -30, -50, 80, -45, -80, 45],
        [30, 60, -30, -58, 80, -45, -80, 45],
        [30, 60, -30, -60, 80, -45, -80, 45],
    ]
    robot_dog.legs_move(hand_lowering_angles, immediately=False, speed=80)
    robot_dog.head_move([[0, 0, -35]], speed=80)
    robot_dog.wait_all_done()


def high_five(dog: "Pidog") -> None:
    """
    Perform a high-five action:
      1. Raise the paw.
      2. Lower it to high-five.
      3. Withdraw the paw.
      4. Move the head and legs for the concluding gesture.
    """
    raise_paw_angles: List[ActionAngles] = [
        [30, 60, 50, 30, 80, -45, -80, 38],
    ]
    lower_paw_angles: List[ActionAngles] = [
        [30, 60, 70, -50, 80, -45, -80, 38],
    ]
    withdraw_paw_angles: List[ActionAngles] = [
        [30, 60, -40, 30, 80, -45, -80, 38],
    ]
    dog.legs_move(raise_paw_angles, immediately=False, speed=80)
    dog.wait_all_done()

    dog.legs_move(lower_paw_angles, immediately=False, speed=94)
    dog.wait_all_done()
    sleep(0.5)

    dog.legs_move(withdraw_paw_angles, immediately=False, speed=80)

    hand_lowering_angles: List[ActionAngles] = [
        [30, 60, -30, -40, 80, -45, -80, 45],
        [30, 60, -30, -50, 80, -45, -80, 45],
        [30, 60, -30, -58, 80, -45, -80, 45],
        [30, 60, -30, -60, 80, -45, -80, 45],
    ]
    dog.legs_move(hand_lowering_angles, immediately=False, speed=80)
    dog.head_move([[0, 0, -35]], speed=80)
    dog.wait_all_done()


def pant(
    dog: "Pidog",
    base_head_angles: ActionAngles = [0, 0, 0],
    pitch_adjustment=0,
    speed=80,
    volume=100,
) -> None:
    """
    Simulate panting by moving the head in a repeated pattern.
    A panting sound is played as well.

    The head moves between two positions in several cycles.
    """
    head_position1 = [base_head_angles[0], base_head_angles[1], base_head_angles[2]]
    head_position2 = [
        base_head_angles[0],
        base_head_angles[1],
        base_head_angles[2] - 10,
    ]
    head_cycle = [head_position1, head_position2, head_position1]
    dog.speak("pant", volume)
    sleep(0.01)
    for _ in range(6):
        dog.head_move(
            head_cycle, pitch_comp=pitch_adjustment, immediately=False, speed=speed
        )
        dog.wait_head_done()


def body_twisting(dog: "Pidog") -> None:
    """
    Make the dog perform a twisting action with its body.
    After twisting, the dog shifts into a two-sit posture.
    """
    twist_position1: ActionAngles = [-80, 70, 80, -70, -20, 64, 20, -64]
    twist_position2: ActionAngles = [-70, 50, 80, -90, 10, 20, 20, -64]
    twist_position3: ActionAngles = [-80, 90, 70, -50, -20, 64, -10, -20]
    twist_sequence: List[ActionAngles] = [
        twist_position2,
        twist_position1,
        twist_position3,
        twist_position1,
    ]

    dog.legs_move(twist_sequence, immediately=False, speed=50)
    dog.wait_all_done()
    sleep(0.3)
    two_sit_angles: List[ActionAngles] = [
        [40, 35, -40, -35, 60, 5, -60, -5],
        [30, 60, -30, -60, 80, -45, -80, 45],
    ]
    dog.legs_move(two_sit_angles, immediately=False, speed=68)
    dog.head_move_raw([[0, 0, -35]], immediately=False, speed=68)
    dog.wait_all_done()


def bark_action(
    dog: "Pidog",
    base_head_angles: ActionAngles = [0, 0, 0],
    bark_label=None,
    volume=100,
) -> None:
    """
    Perform a bark action:
      1. Move head and legs into a barking pose.
      2. Optionally speak the bark sound.
      3. Transition to a second set of angles.
    """
    head_up = [base_head_angles[0], base_head_angles[1], base_head_angles[2] + 20]
    head_down = [base_head_angles[0], base_head_angles[1], base_head_angles[2]]

    leg_angles_first = dog.legs_angle_calculation(
        [[0, 100], [0, 100], [30, 90], [30, 90]]
    )
    leg_angles_second = dog.legs_angle_calculation(
        [[-20, 90], [-20, 90], [0, 90], [0, 90]]
    )

    if bark_label is not None:
        dog.speak(bark_label, volume)
    dog.legs_move([leg_angles_first], immediately=True, speed=85)
    dog.head_move([head_up], immediately=True, speed=85)
    dog.wait_all_done()
    sleep(0.01)
    dog.legs_move([leg_angles_second], immediately=True, speed=85)
    dog.head_move([head_down], immediately=True, speed=85)
    dog.wait_all_done()
    sleep(0.01)


def shake_head(dog: "Pidog", base_head_angles: ActionAngles = [0, 0, -20]) -> None:
    """
    Shake head quickly by moving left, then right, then centering.
    """
    head_left = [[base_head_angles[0] + 40, base_head_angles[1], base_head_angles[2]]]
    head_right = [[base_head_angles[0] - 40, base_head_angles[1], base_head_angles[2]]]
    head_center = [[base_head_angles[0], base_head_angles[1], base_head_angles[2]]]
    dog.head_move(head_left, immediately=False, speed=92)
    dog.head_move(head_right, immediately=False, speed=92)
    dog.head_move(head_center, immediately=False, speed=92)
    dog.wait_all_done()


def shake_head_smooth(dog: "Pidog", pitch_adjustment=0, amplitude=40, speed=90) -> None:
    """
    Smoothly shake the head by generating a sine wave for the yaw.
    """
    angles_sequence = []
    for i in range(0, 31, 2):
        yaw_value = round(amplitude * sin(pi / 10 * i), 2)
        # Keeping roll constant at 0 and using pitch_adjustment as pitch value.
        angles_sequence.append([yaw_value, 0, pitch_adjustment])
    dog.head_move_raw(angles_sequence, speed=speed)
    dog.wait_all_done()


def bark(
    dog: "Pidog",
    base_head_angles: ActionAngles = [0, 0, 0],
    pitch_adjustment=0,
    roll_adjustment=0,
    volume=100,
) -> None:
    """
    Perform a single bark:
      1. Raise the head.
      2. Play bounce bark sound.
      3. Lower the head back.
    """
    head_raised = [base_head_angles[0], base_head_angles[1], base_head_angles[2] + 25]
    head_lowered = [base_head_angles[0], base_head_angles[1], base_head_angles[2]]
    dog.wait_head_done()
    dog.head_move(
        [head_raised],
        pitch_comp=pitch_adjustment,
        roll_comp=roll_adjustment,
        immediately=True,
        speed=100,
    )
    dog.speak("single_bark_1", volume)
    dog.wait_head_done()
    sleep(0.08)
    dog.head_move(
        [head_lowered],
        pitch_comp=pitch_adjustment,
        roll_comp=roll_adjustment,
        immediately=True,
        speed=100,
    )
    dog.wait_head_done()
    sleep(0.5)


def push_up(dog: "Pidog", speed=80) -> None:
    """
    Perform a push-up action.
    The head is moved first then the push-up action is triggered.
    """
    dog.head_move([[0, 0, -80], [0, 0, -40]], speed=speed - 10)
    dog.do_action("push_up", speed=speed)
    dog.wait_all_done()


def howling(dog: "Pidog", volume=100) -> None:
    """
    Perform a howling action with coordinated body, head, and LED changes.
    The dog changes posture, sets a LED color mode, then howls and adjusts posture again.
    """
    dog.do_action("sit", speed=80)
    dog.head_move([[0, 0, -30]], speed=95)
    dog.wait_all_done()

    dog.rgb_strip.set_mode("speak", color="cyan", bps=0.6)
    dog.do_action("half_sit", speed=80)
    dog.head_move([[0, 0, -60]], speed=80)
    dog.wait_all_done()
    dog.speak("howling", volume)
    dog.do_action("sit", speed=60)
    dog.head_move([[0, 0, 10]], speed=70)
    dog.wait_all_done()

    dog.do_action("sit", speed=60)
    dog.head_move([[0, 0, 10]], speed=80)
    dog.wait_all_done()

    sleep(2.34)
    dog.do_action("sit", speed=80)
    dog.head_move([[0, 0, -40]], speed=80)
    dog.wait_all_done()


def attack_posture(dog: "Pidog") -> None:
    """
    Set the dog’s posture to an aggressive attack stance.
    """
    calculated_angles = dog.legs_angle_calculation(
        [[-20, 90], [-20, 90], [0, 90], [0, 90]]
    )
    dog.legs_move([calculated_angles], immediately=True, speed=85)
    dog.wait_legs_done()
    sleep(0.01)


def lick_hand(dog: "Pidog") -> None:
    """
    Simulate licking a hand:
      1. Sit and adjust head first.
      2. Move legs and head into a licking position.
      3. Alternate between two leg positions while keeping head steady.
      4. Finally, lower the hand.
    """
    leg_position_initial: List[ActionAngles] = [[30, 45, 70, -32, 80, -55, -80, 45]]
    head_positions: List[ActionAngles] = [
        [-22, -23, -45],
        [-22, -23, -35],
    ]
    leg_position_alternate: List[ActionAngles] = [
        [30, 45, 70, -32, 80, -55, -80, 45],
        [30, 45, 66, -36, 80, -55, -80, 45],
    ]

    dog.do_action("sit", speed=80)
    dog.head_move([[0, 0, -40]], immediately=True, speed=70)
    dog.wait_head_done()
    dog.wait_legs_done()

    dog.legs_move(leg_position_initial, immediately=False, speed=80)
    dog.head_move(head_positions, immediately=False, speed=70)
    dog.wait_head_done()
    dog.wait_legs_done()
    for _ in range(3):
        dog.legs_move(leg_position_alternate, immediately=False, speed=90)
        dog.head_move(head_positions, immediately=False, speed=80)
        dog.wait_head_done()
        dog.wait_legs_done()

    hand_lowering_angles: List[ActionAngles] = [
        [30, 60, -30, -40, 80, -45, -80, 45],
        [30, 60, -30, -50, 80, -45, -80, 45],
        [30, 60, -30, -58, 80, -45, -80, 45],
        [30, 60, -30, -60, 80, -45, -80, 45],
    ]
    dog.legs_move(hand_lowering_angles, immediately=False, speed=80)
    dog.head_move([[0, 0, -35]], speed=80)
    dog.wait_all_done()


def waiting(dog: "Pidog", pitch_adjustment: float) -> None:
    """
    Slightly adjust head posture to simulate waiting.
    One of four preset head adjustments is randomly chosen.
    """
    pos1 = [0, 7, pitch_adjustment + 5]
    pos2 = [0, -7, pitch_adjustment + 5]
    pos3 = [0, 7, pitch_adjustment - 5]
    pos4 = [0, -7, pitch_adjustment - 5]
    possible_positions = [pos1, pos2, pos3, pos4]
    weights = [1, 1, 1, 1]
    chosen_position = random.choices(possible_positions, weights)[0]
    dog.head_move([chosen_position], immediately=False, speed=5)
    dog.wait_head_done()


def feet_shake(dog: "Pidog", step_count=None) -> None:
    """
    Shake the feet by modifying the leg current angles.
    After shaking, return to the sit posture.
    """
    assert dog.leg_current_angles is not None, "Leg current angles should not be None"
    current_leg_angles = list(dog.leg_current_angles)

    modified_angles1 = list(current_leg_angles)
    modified_angles2 = list(current_leg_angles)
    modified_angles1[0] += 10
    modified_angles1[1] -= 25
    modified_angles2[2] -= 10
    modified_angles2[3] += 25

    shake_pattern1 = [
        modified_angles1,
        modified_angles1,
        modified_angles2,
        modified_angles2,
    ]
    shake_pattern2 = [modified_angles1, current_leg_angles]
    shake_pattern3 = [modified_angles2, current_leg_angles]

    possible_shake_patterns = [shake_pattern1, shake_pattern2, shake_pattern3]
    pattern_weights = [1, 1, 1]
    chosen_shake_pattern = random.choices(possible_shake_patterns, pattern_weights)[0]

    if step_count is None:
        step_count = random.randint(1, 2)

    for _ in range(step_count):
        dog.legs_move(chosen_shake_pattern, immediately=False, speed=45)
        dog.wait_legs_done()

    dog.do_action("sit", speed=60)
    dog.head_move([[0, 0, -40]], speed=80)
    dog.wait_all_done()


def sit_2_stand(dog: "Pidog", speed=75) -> None:
    """
    Transition from a sit to a stand position.
    """
    stand_angles = dog.actions_dict["stand"][0][0]
    intermediate_angles = [25, 25, -25, -25, 70, -25, -70, 25]

    transition_sequence = [
        intermediate_angles,
        stand_angles,
    ]

    dog.legs_move(transition_sequence, immediately=False, speed=speed)
    dog.wait_legs_done()


def relax_neck(dog: "Pidog", pitch_adjustment=-35) -> None:
    """
    Relax the neck by smoothly rotating it followed by a stretch.
    """
    neck_turn_sequence = []
    for i in range(21):
        yaw_angle = round(10 * sin(pi / 10 * i), 2)
        roll_angle = round(45 * sin(pi / 10 * i), 2)
        pitch_angle = round(20 * sin(pi / 10 * i - pi / 2) + pitch_adjustment, 2)
        neck_turn_sequence.append([yaw_angle, roll_angle, pitch_angle])
    dog.head_move_raw(neck_turn_sequence, speed=80)
    dog.wait_all_done()
    sleep(0.3)

    neck_stretch_sequence: List[ActionAngles] = [
        [0, 0, 5 + pitch_adjustment],
        [0, 45, 5 + pitch_adjustment],
        [0, 25, 5 + pitch_adjustment],
        [0, 45, 5 + pitch_adjustment],
        [0, 25, 5 + pitch_adjustment],
        [0, 0, 5 + pitch_adjustment],
        [0, 0, 5 + pitch_adjustment],
        [0, 0, 5 + pitch_adjustment],
        [0, -45, 5 + pitch_adjustment],
        [0, -25, 5 + pitch_adjustment],
        [0, -45, 5 + pitch_adjustment],
        [0, -25, 5 + pitch_adjustment],
        [0, 0, pitch_adjustment],
    ]
    dog.head_move_raw(neck_stretch_sequence, speed=80)
    dog.wait_all_done()


def nod(
    dog: "Pidog",
    pitch_adjustment: Union[int, float] = -35,
    amplitude: Union[int, float] = 20,
    step_count=2,
    speed=90,
) -> None:
    """
    Perform a nodding movement.
    The head is moved in a cosine-shaped pattern.
    """
    nod_sequence = []
    for i in range(0, 20 * step_count + 1, 2):
        yaw_value = 0
        roll_value = 0
        pitch_value = round(
            amplitude * cos(pi / 10 * i) - amplitude + pitch_adjustment, 2
        )
        nod_sequence.append([yaw_value, roll_value, pitch_value])
    dog.head_move_raw(nod_sequence, speed=speed)
    dog.wait_all_done()


def think(dog: "Pidog", pitch_adjustment: Union[int, float] = 0) -> None:
    """
    Perform a 'thinking' head gesture.
    """
    head_position = [[20, -15, 15 + pitch_adjustment]]
    dog.head_move_raw(head_position, speed=80)
    dog.wait_all_done()


def recall(dog: "Pidog", pitch_adjustment: Union[int, float] = 0) -> None:
    """
    Perform a 'recall' head gesture.
    """
    head_position = [[-20, 15, 15 + pitch_adjustment]]
    dog.head_move_raw(head_position, speed=80)
    dog.wait_all_done()


def head_down_left(dog: "Pidog", pitch_adjustment: Union[int, float] = 0) -> None:
    """
    Move the head downward and to the left.
    """
    head_position = [[25, 0, -35 + pitch_adjustment]]
    dog.head_move_raw(head_position, speed=80)
    dog.wait_all_done()


def head_down_right(dog: "Pidog", pitch_adjustment: Union[int, float] = 0) -> None:
    """
    Move the head downward and to the right.
    """
    head_position = [[-25, 0, -35 + pitch_adjustment]]
    dog.head_move_raw(head_position, speed=80)
    dog.wait_all_done()


def fluster(dog: "Pidog", pitch_adjustment: Union[int, float] = 0) -> None:
    """
    Simulate a flustered gesture.
    The head moves in a small oscillation for a few cycles.
    """
    head_oscillation = [
        [-10, 0, pitch_adjustment],
        [0, 0, pitch_adjustment],
        [10, 0, pitch_adjustment],
        [0, 0, pitch_adjustment],
    ]
    # Repeating the oscillation five times.
    for _ in range(5):
        dog.head_move_raw(head_oscillation, speed=100)
        dog.wait_all_done()


def alert(dog: "Pidog", pitch_adjustment: Union[int, float] = 0) -> None:
    """
    Perform an alert action with legs and head adjustments.
    After executing the sequence, the head pans left and right.
    """
    legs_sequence: List[ActionAngles] = [
        [30, 50, -30, -50, 80, -45, -80, 45],
        [30, 60, -30, -60, 88, -45, -88, 45],
    ]
    head_sequence: List[ActionAngles] = [
        [0, 0, -5 + pitch_adjustment],
        [0, 0, 10 + pitch_adjustment],
    ]
    dog.legs_move(legs_sequence, immediately=False, speed=100)
    dog.head_move_raw(head_sequence, immediately=False, speed=100)
    dog.wait_all_done()

    dog.head_move_raw([[30, 0, pitch_adjustment]], speed=100)
    dog.wait_all_done()
    sleep(1)
    dog.head_move_raw([[-30, 0, pitch_adjustment]], speed=100)
    dog.wait_all_done()
    sleep(1)

    dog.head_move_raw([[0, 0, pitch_adjustment]], speed=100)
    dog.wait_all_done()


def surprise(
    dog: "Pidog",
    pitch_adjustment: Union[int, float] = 0,
    status: Literal["sit", "stand"] = "sit",
) -> None:
    """
    Perform a surprise expression. The sequence depends on whether the dog is sitting or standing.
    """
    if status == "sit":
        legs_sequence: List[ActionAngles] = [
            [30, 50, -30, -50, 80, -45, -80, 45],
            [30, 80, -30, -80, 88, -45, -88, 45],
        ]
        head_sequence = [[0, 0, -5 + pitch_adjustment], [0, 0, 10 + pitch_adjustment]]
        dog.legs_move(legs_sequence, immediately=False, speed=100)
        dog.head_move_raw(head_sequence, immediately=False, speed=100)
        dog.wait_all_done()

        sleep(1)

        dog.legs_move(
            [[30, 60, -30, -60, 80, -45, -80, 45]], immediately=False, speed=80
        )
        dog.head_move_raw([[0, 0, pitch_adjustment]], immediately=False, speed=80)
        dog.wait_all_done()

    elif status == "stand":
        legs_sequence = [
            [40, 10, -40, -10, 60, -5, -60, 5],
            [40, 25, -40, -25, 60, 0, -60, 0],
        ]
        head_sequence = [[0, 0, pitch_adjustment], [0, 0, 10 + pitch_adjustment]]
        dog.legs_move(legs_sequence, immediately=False, speed=80)
        dog.head_move_raw(head_sequence, immediately=False, speed=80)
        dog.wait_all_done()

        sleep(1)

        dog.legs_move([[40, 15, -40, -15, 60, 5, -60, -5]], immediately=False, speed=80)
        dog.head_move_raw([[0, 0, pitch_adjustment]], immediately=False, speed=80)
        dog.wait_all_done()


def stretch(dog: "Pidog") -> None:
    """
    Make the dog perform a stretch.
    The sequence first extends the body then transitions into a two-sit position.
    """
    head_extension: List[ActionAngles] = [
        [0, 0, 25],
    ]
    leg_extension: List[ActionAngles] = [
        [-80, 70, 80, -70, -20, 64, 20, -64],
        [-80, 70, 80, -70, -20, 64, 20, -64],
        [-65, 70, 65, -70, -20, 64, 20, -64],
        [-80, 70, 80, -70, -20, 64, 20, -64],
        [-65, 70, 65, -70, -20, 64, 20, -64],
    ]
    dog.legs_move(leg_extension, immediately=False, speed=55)
    dog.head_move_raw(head_extension, immediately=False, speed=55)
    dog.wait_all_done()
    sleep(0.3)
    two_sit_angles: List[ActionAngles] = [
        [40, 35, -40, -35, 60, 5, -60, -5],
        [30, 60, -30, -60, 80, -45, -80, 45],
    ]
    dog.legs_move(two_sit_angles, immediately=False, speed=68)
    dog.head_move_raw([[0, 0, -35]], immediately=False, speed=68)
    dog.wait_all_done()
