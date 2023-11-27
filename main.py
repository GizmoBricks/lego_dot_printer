"""
This program prints PBM images from the Mindstorms Hub Slot.

File type should be P1 - ASCII (plain).
For more details about PBM format visit:
https://netpbm.sourceforge.net/doc/pbm.html
https://en.wikipedia.org/wiki/Netpbm

PBM file may be created with:
    1. Paint.NET FileType plugin which loads and saves image files
        in PBM file formats:
        https://tinyurl.com/5a4buav5
    2. Photoshop can work with PBM files, but it can not save PBM files
        in ASCII format, so some plugin should be used.
        Photoshop PBM plugin:
        https://tinyurl.com/yv6v65n8
    3. GIMP works with PBM format out of the box.
        https://www.gimp.org/

How to load PBM file into the Mindstorms Hub:
1. Save your picture as *.pbm in ASCII mode.
2. Open this *.pbm file with notepad or any simular app.
3. Select all data in the file and copy it.
4. Create python project in the Mindstorms app or SPIKE Legacy app.
5. Clear python project.
6. Paste your data into python project.
7. Select slot on the hub and press download. Slot should be different
    from the slot where current program is stored.
7.1 You can also press run button instead of download button.
    In this case the Mindstorms app console return SyntaxError -
    it is fine, file anyway will be stored on the hub.
8. Now you can get path to this file with the get_slot_path function.

Building instruction for printer:
ADD_LINK (in progress)

GitHub repository:
https://github.com/GizmoBricks/lego_dot_printer/

Links:
GizmoBricksChannel@gmail.com
https://github.com/GizmoBricks
https://www.youtube.com/@GizmoBricks/

GizmoBricks
09.11.2023

"""
# If you use Spike Prime app, uncomment imports from spike
# and comment imports from mindstorms
# from spike.control import wait_for_seconds, Timer
from mindstorms.control import wait_for_seconds, Timer
from math import pi
import hub

# Constants:

# Number of the slot on the Hub with picture [0-19]:
SLOT_TO_PRINT = 0
# Allow user to select a slot from the hub or use
# the SLOT_TO_PRINT constant:
ALLOW_TO_SELECT_SLOT = True

WAIT_FOR_TAP_AFTER_CALIBRATION = False

# Diameter of the single dot in millimeters. It represents the thickness
# of the pen line.
DOT_DIMENSION = 1  # mm

# Determines whether to print along the shortest path or print
# every line from the first dot.
SHORTEST_PATH = True
# Determines whether to apply backlash correction or not.
BACKLASH_CORRECTION = True
# Distance from the target position in millimeters
# the motor must move backwards before it can move
# to the target position:
CORRECTION_VALUE = 1  # mm
# Additional information about the shortest path printing
# and backlash correction:
# SHORTEST_PATH | BACKLASH_CORRECTION |    Accuracy     | Time of printing
#      True     |         True        |       High      |Depends on the picture
#      True     |        False        |       Low       | Short
#     False     |         True        |       High      |Depends on the picture
#     False     |        False        | Low (first dot) |Depends on the picture
#               |                     |  High (others)  |

# Absolute position of the pen motor in degrees.
PEN_DRAWS = 80  # °
PEN_DOESNT_DRAW = 100  # °

# Gear ratio of the axes gearboxes between the motor and the wheels.
# Gear ratio = number of driven gear teeth / number of drive gear teeth.
# For multi-stage gearboxes, this is the multiplication
# of the gear ratios for each stage.
X_GEAR_RATIO = 8
Y_GEAR_RATIO = 24

# Wheel diameter for wheel or pitch diameter gear in mm.
X_WHEEL_DIAMETER = 24  # mm
Y_WHEEL_DIAMETER = 56  # mm

# Motors initialization:
X_MOTOR = hub.port.C.motor
Y_MOTOR = hub.port.D.motor
PEN_MOTOR = hub.port.E.motor

# Speed of the axes and pen motors in percent [0-100]%:
X_SPEED = 100
Y_SPEED = 100
PEN_SPEED = 100

# Color Sensor initialization:
X_SENSOR = hub.port.A.device
# Colors for calibration:
X_ZERO_COLOR = 'red'
X_ZERO_COLOR_2 = 'black'
X_END_COLOR = 'yellow'

# For future releases:
# PAPER_SENSOR = hub.port.B.device


# Here should be a large descriptor for the Axis class.
# I need some time for its implementation and in the MicroPython
# the __set_name__ magick method doesn't exist yet.
# So, the descriptor will be done in the future version, and this class
# may make some strange things in some cases.
class Axis:
    VALID_DIRECTIONS = (-1, 1)

    def __init__(self, motor,
                 gear_ratio: float, wheel_diameter: float,
                 dot_dimension: float = 1,
                 speed: int = 100, direction: int = 1,
                 color_sensor=None, zero_colors=('0', '0'),
                 end_colors=('0', '0'),
                 backlash_correction: bool = False, correction_value: float = 0
                 ):
        """
        Initialize the Axis object.

        Args:
            motor: The motor object used for control.
            gear_ratio: The gear ratio of the motor.
            wheel_diameter: The diameter of the wheel connected to the motor.
            dot_dimension: The dimension of the dot.
            speed: The default speed of the motor.
            direction: The default direction of motion.
            color_sensor: The sensor object used for color detection.
            zero_colors: Tuple of colors for calibration at zero position.
            end_colors: Tuple of colors for calibration at the end position.
            backlash_correction: Whether to apply backlash correction or not.
            correction_value: Value used for backlash correction.
        """
        self.motor = motor
        self.gear_ratio = gear_ratio
        self.wheel_diameter = wheel_diameter
        self.dot_dimension = dot_dimension
        self.speed = speed

        if direction in self.VALID_DIRECTIONS:
            self.direction = direction
        else:
            raise ValueError(' direction is not one of the allowed '
                             'values: {}'.format(self.VALID_DIRECTIONS))

        self.sensor = color_sensor
        self.zero_colors = zero_colors
        self.end_colors = end_colors
        self.backlash_correction = backlash_correction
        self.correction_value = correction_value

        self.correction_step = self._calculate_step(self.correction_value)
        self.step = self._calculate_step(self.dot_dimension)

        self.end = self._read_end_from_file()
        self.length = self._calculate_length()

    @staticmethod
    def _read_end_from_file():
        """
        Read the end position from a settings file.
        """
        try:
            with open('settings.txt', 'r') as file:
                if file.readline().rstrip() == __name__:
                    return int(file.readline().rstrip())
        except OSError:
            pass
        return None

    def _calculate_step(self, dot_dim: float):
        """
        Calculate the step based on gear ratio, wheel diameter,
        and dot dimension.
        """
        step = int(round(
            360 * dot_dim * self.gear_ratio / (pi * self.wheel_diameter))
        )
        return step

    def _calculate_length(self):
        """
        Calculate the length based on the end position and step size.
        """
        if self.end is None:
            return None
        return int(self.end / self.step)

    def _check_target(self, target_position):
        """
        Check if the target position is within the axis limits.

        Args:
            target_position: The target position to be checked.
        Raises:
            RuntimeError: If the target position
                          is outside the limits of the axis.
        """
        if self.end is not None:
            min_ = min(self.end, 0)
            max_ = max(self.end, 0)

            if not (min_ <= target_position <= max_):
                raise RuntimeError(
                    'Target position {0} is outside the axis limits[{1}, {2}].'
                    ''.format(target_position, min_, max_))

    def _run_until_color(self, color, direction: int):
        """
        Run the motor until a specific color is detected by the sensor.

        Args:
            color: The color to be detected.
            direction: The direction of motor movement.
        """
        color_values = {'black': 0, 'violet': 1, 'blue': 3, 'cyan': 4,
                        'green': 5, 'yellow': 7, 'red': 9, 'white': 10,
                        None: -1}
        if isinstance(color, str):
            color_value = color_values.get(color)
        else:
            color_value = color

        if self.sensor.get()[1] != color_value:
            self.motor.run_at_speed(self.speed * direction)
            while self.sensor.get()[1] != color_value:
                continue
            self.motor.brake()

    def wait_until_motion_done(self):
        """
        Wait until the motor finishes its motion.
        """
        while self.motor.busy(1):
            continue

    def set_steps(self, dot_dim: float, correction: float,
                  gear_ratio: float, wheel_dim: float) -> None:
        """
        Set the step size and correction step based on dot dimension,
        correction value, gear ratio, and wheel dimension.

        Args:
            dot_dim: The diameter in mm of the dot.
            correction: The correction value in mm.
            gear_ratio: The gear ratio of the gearbox
                        between the motor and the wheel.
            wheel_dim: The diameter of the wheel or pitch diameter of the gear.

        Should be replaced with descriptor in the future.
        """
        self.dot_dimension = dot_dim
        self.gear_ratio = gear_ratio
        self.wheel_diameter = wheel_dim
        self.correction_value = correction

        self.correction_step = self._calculate_step(self.correction_value)
        self.step = self._calculate_step(self.dot_dimension)

    def calibrate(self, first_color='0', second_color='0', *,
                  set_as_zero: bool = True, direction: int = -1):
        """
        Calibrate the motor based on feedback of the color sensor.

        Args:
        - motor_obj: The motor object to calibrate.
        - sensor_obj (optional): The sensor object used for color detection.
                                (default: None)
        Keyword arguments:
        - direction (int, optional): Direction of motor movement, 1 or -1.
                                    (default: 1)
        - set_as_zero (bool, optional): Whether to reset motor position.
                                        (default: True)
        - do_second_step (bool, optional): Flag to perform
                                        a second calibration step.
                                        (default: False)
        - speed (int, optional): Speed of motor movement. (default: 100)
        - first_color (str, optional): The first color to detect.
                                    (default: red)
        - second_color (str, optional): The second color
                                        for the second step. (default: None)

        Returns:
        - The calibrated motor position.

        Raises:
        - ValueError: If direction is not valid.
        """
        if first_color != '0' and self.sensor:

            self._run_until_color(first_color, direction)

            if second_color != '0':
                self._run_until_color(second_color, -direction)

        if set_as_zero:
            wait_for_seconds(0.1)
            self.motor.preset(0)

        wait_for_seconds(0.1)

        return self.motor.get()[1]

    def calibrate_zero(self):
        zero_colors = self.zero_colors
        if isinstance(zero_colors, str):
            zero_colors = [zero_colors]
        return self.calibrate(*zero_colors,
                              direction=-self.direction)

    def calibrate_end(self):
        if self.end is None:
            end_colors = self.end_colors
            if isinstance(end_colors, str):
                end_colors = [end_colors]
            self.end = self.calibrate(*end_colors,
                                      set_as_zero=False,
                                      direction=self.direction)
            with open('settings.txt', 'w') as file:
                file.write(__name__ + '\n')
                file.write(str(self.end))

        self.length = int(self.end / self.step)
        return self.end

    def go_home(self):
        self.motor.run_to_position(0, self.speed)

    def run_to_position(self, position, wait: bool = False,
                        mode: str = 'degrees'):
        """
        Run the motor to a specific position.

        Args:
            position: The target position to move to.
            wait: Whether to wait for the motion to complete or not.
            mode:
        """
        valid_modes = ('degrees', 'steps')

        if mode not in valid_modes:
            raise ValueError('Mode is not one of the allowed '
                             'values: {}'.format(valid_modes))

        if mode == 'degrees':
            target = position
        else:
            target = self.step * position

        self._check_target(target)
        current_position = self.motor.get()[1]
        if target < current_position and self.backlash_correction:
            self.motor.run_to_position(target - self.correction_step,
                                       self.speed)
            self.wait_until_motion_done()
        self.motor.run_to_position(target, self.speed)
        if wait:
            self.wait_until_motion_done()

    def move_steps(self, steps, wait: bool = False):
        target = self.motor.get()[1] + self.step * self.direction * steps
        self._check_target(target)
        if wait:
            self.motor.run_to_position(target, self.speed)

    def get_position(self):
        return self.motor.get()[1]


class Pen:
    """
    drawing_position and non_drawing_position should be in range [0-359]
    if speed > 100 it's set to 100, if it's a negative value,
    it's set to a positive value.
    All those are implemented outside the Pen class.
    """
    def __init__(self, pen_motor,
                 drawing_position: int, non_drawing_position: int,
                 speed: int = 100):
        self.motor = pen_motor
        self.drawing_position = drawing_position
        self.non_drawing_position = non_drawing_position
        self.speed = speed

    def info(self):
        print('Pen motor: {:>16}'.format(str(self.motor)))
        print('Drawing position: {:>9}'.format(self.drawing_position))
        print('Non drawing position: {:>5}'.format(self.non_drawing_position))
        print('Speed: {:>20}'.format(self.speed))

    def put_up(self):
        run_to_absolute_position(self.motor, self.non_drawing_position,
                                 self.speed)

    def put_down(self):
        run_to_absolute_position(self.motor, self.drawing_position, self.speed)

    def put_dot(self):
        self.put_down()
        self.put_up()


# This function can be a method of the Pen class,
# but it's also useful outside any classes.
def run_to_absolute_position(motor,
                             position: int,
                             speed: int = 100,
                             direction: str = 'shortest path'):
    """
    Move the motor to an absolute position in a specified direction.

    Args:
    - motor: The motor object used for movement.
    - position (int): The absolute position to which the motor
                      should move (0-359, inclusive).
    - speed (int, optional): Speed of motor movement. (default: 100)
    - direction (str, optional): The direction in which the motor
        should move. ('shortest path' (default), 'clockwise',
        or 'counterclockwise').

    Raises:
    - ValueError: If the given position is outside the range 0-359
                  or if the direction is invalid.
    """
    if not (0 <= position <= 359):
        raise ValueError(
            ' position is not in the range 0-359 (both inclusive)')

    valid_directions = ('shortest path', 'clockwise', 'counterclockwise')
    if direction not in valid_directions:
        raise ValueError('direction is not one of the allowed '
                         'values: {}'.format(valid_directions))

    relative_position, absolute_position = motor.get()[1:3]
    absolute_position = absolute_position % 360
    angle_difference = position - absolute_position

    if absolute_position > position:
        clockwise = angle_difference + 360
        counterclockwise = angle_difference
    else:
        clockwise = angle_difference
        counterclockwise = angle_difference - 360

    if direction == 'shortest path':
        if abs(clockwise) < abs(counterclockwise):
            target = relative_position + clockwise
        else:
            target = relative_position + counterclockwise

    elif direction == 'clockwise':
        target = relative_position + clockwise
    else:
        target = relative_position + counterclockwise

    motor.run_to_position(target, speed)

    while motor.busy(1):
        continue


def two_digits_image(number: int):
    """
    Generate a 5x5 image representation of a two-digit number
    using predefined patterns.

    Args:
    - number (int): A two-digit number (10-99, both inclusive)
                    for which the image is generated.

    Returns: An image representation based on the input number.
    Raises:
    - ValueError: If the input number is not within the range 10-99
                  (both inclusive).
    """
    if not (10 <= number <= 99):
        raise ValueError('number is not in the range 10-99 (both inclusive).')

    digits_2 = ['9999999999', '9090909090', '9909999099', '9909990999',
                '9999990909', '9990990999', '9990999999', '9909090909',
                '9999009999', '9999990999']

    digits_3 = ['999909909909999', '090090090090090', '999009999900999',
                '999009999009999', '909909999009009', '999900999009999',
                '999900999909999', '999009009009009', '999909999909999',
                '999909999009999']

    tens, ones = divmod(number, 10)

    image = ''

    for i in range(5):
        start = 2 * i
        end = start + 2
        if tens == 1:
            start_3 = 3 * i
            second_digit = digits_3[ones][start_3:start_3 + 3]
        else:
            second_digit = '0' + digits_2[ones][start:end]
        image = image + digits_2[tens][start:end] + second_digit + ':'

    return hub.Image(image)


def select_on_display(range_, two_digits_font=True):
    """
    Allows users to interactively select and display a value
    from a given range on a display.

    Parameters:
    - range_ (iterable, optional): A sequence of values to select from.
    - two_digits_font (bool, optional): Determines whether to display
                                        two-digit values
                                        in a special font.
                                        (default: True)

    Returns:
    - selected_value: The value selected from the provided range.

    Note:
    - This function assumes the existence of external functions:
        - two_digits_image(int): Generate a 5x5 image representation
          of a two-digit number using predefined patterns.
    - This function returns a value of the same type as the type
      of the selected element from the given _range.
    """
    if not isinstance(range_, (str, range, tuple, list)):
        raise TypeError('the given argument must be of type '
                        'str, range, tuple or list')

    def _get_value_from_callback(value):
        nonlocal gesture
        gesture = value

    def _get_data_to_show(i: int):
        """
        Retrieves the formatted data to display on the output device
        based on the selected index.

        Parameters:
        - i (int): The index of the value in the provided range
                   to generate display data for.

        Returns:
        - _data_to_show (str): The formatted data to be displayed.
        - _delay (int): The delay time for displaying the data
                       (in milliseconds).
        - _fade (int): The fade effect type for displaying the data.
        """
        nonlocal range_
        nonlocal two_digits_font

        value = range_[i]
        _data_to_show = ''
        _delay = 0
        _fade = 0

        if isinstance(value, (int, str)) and str(value).isdigit():
            value = int(value)
            if 10 <= value <= 99 and two_digits_font:
                _data_to_show = two_digits_image(value)

        if not _data_to_show:
            _data_to_show = str(value)
            if len(_data_to_show) > 1:
                _data_to_show = _data_to_show + ' '
                _delay = 500
                _fade = 4

        return _data_to_show, _delay, _fade

    gesture = -1
    selected = 0
    hub.led(255, 0, 255)
    range_len = len(range_)

    if range_len != 1:
        print('Select value on the Hub.\n'
              'Use left and right buttons to select value, '
              'tap the hub to confirm your choice.')

        hub.button.left.presses()
        hub.button.right.presses()

        hub.motion.gesture(callback=_get_value_from_callback)

        while gesture != 0:
            presses = hub.button.right.presses() - hub.button.left.presses()
            new_selected = selected + presses
            selected = new_selected % range_len

            data_to_show, delay, fade = _get_data_to_show(selected)

            hub.display.show(data_to_show, delay=delay, wait=True, fade=fade)
        hub.motion.gesture(callback=None)

    print(' \n"{}" was selected.'.format(range_[selected]))

    hub.display.clear()
    hub.led(10)

    return range_[selected]


def get_slot_path(slot: int = 0,
                  extension: str = '.py',
                  do_check: bool = False,
                  check_word: str = 'P1') -> str:
    """
    Retrieve the path associated with a given slot number
     from the 'projects/.slots' file.

    Args:
    - slot (int, optional): The slot number (0-19 inclusive) to retrieve
                            the path for.
    - extension (str, optional): The file extension to append the path
                                 (default: '.py').
    - do_check (bool, optional): Flag to indicate whether to perform
                                 a file format check (default: False).
    - check_word (str, optional): The word used for file format checking
                                  (default: 'P1' for PBM ASCII format).

    Returns:
    - str: The path corresponding to the provided slot number.

    Raises:
    - ValueError: If the slot is not within
                  the range 0-19 (both inclusive).
    - RuntimeError: If the slot is empty.
                    If the file format check fails.
    - OSError: If the file extension is different
               from the extension argument.

    Note: the function was tested with Mindstorms app
    and SPIKE Legacy app on Mindstorms hub.
    If you can test it with SPIKE 3 app on the Spike Prime hub,
    please, give me feedback (GizmoBricksChannel@gmail.com)
    """

    if not (0 <= slot <= 19):
        raise ValueError('Slot is not in the range 0-19 (both inclusive).\n'
                         'Check the slot argument. It is {}, '
                         'but it should be in range [0-19].'.format(slot))

    with open('projects/.slots', 'r') as slots_file:
        slots_content = slots_file.readline()

    parsing_start = slots_content.find((str(slot) + ': '), 0)

    if (slots_content.find('1', parsing_start - 1, parsing_start) == -1 and
            parsing_start != -1):
        parsing_end = slots_content.find('},', parsing_start)
        id_start = slots_content.find("'id': ", parsing_start, parsing_end) + 6
        id_end = slots_content.find(", '", id_start, parsing_end)
        path = 'projects/{}/__init__{}'.format(slots_content[id_start:id_end],
                                               extension)
        # open() can reach OSError, if the file extension is different
        # from the extension argument.
        with open(path) as file:
            if file.readline().split()[0] != check_word and do_check:
                raise RuntimeError('file format check failed.')
        return path
    else:
        raise RuntimeError('Slot {} is empty.\n Try to upload file again, '
                           'or try another slot.'.format(slot))


def select_slot(let_select: bool = True, default_slot: int = 0) -> tuple:
    """
    Selects a slot based on certain conditions and returns
    the selected slot along with its corresponding path.

    Args:
    - let_select (bool, optional): If True, selects a slot
                                   from a predefined range (0 to 19).
                                   If False, selects the default_slot.
    - default_slot (int, optional): The default slot to select
                                    if let_select is False.

    Returns:
    - Tuple[int, str]: A tuple containing the selected slot (int)
                       and its corresponding path (str).

    Raises:
    - RuntimeError: If no valid slots are available.

    Note:
    - This function assumes the existence of external functions:
        - get_slot_path(slot: int) -> str: Retrieve the path associated
            with a given slot number from the 'projects/.slots' file.
        - select_on_display(slots: iterable) -> int: Allows users
            to interactively select and display a value
            from a given range on a display.
    """
    slots = []
    paths = []

    if let_select:
        start_slot, stop_slot = 0, 20
    else:
        start_slot, stop_slot = default_slot, default_slot + 1

    for i in range(start_slot, stop_slot):
        try:
            path = get_slot_path(i, do_check=True)
        except (RuntimeError, OSError):
            continue
        else:
            slots.append(i)
            paths.append(path)

    if not slots:
        raise RuntimeError(
            'No valid slots are available.\n'
            'All slots are empty, or no one slot contains a correct file.\n'
            'Try to upload files into slots again\n'
            'or check files format, it should be PBM ASCII file.\n'
            'To learn more about PBM files visit: '
            'https://en.wikipedia.org/wiki/Netpbm')

    if len(slots) == 1:
        selected_index = 0
    else:
        selected_slot = select_on_display(slots)
        selected_index = slots.index(selected_slot)

    return slots[selected_index], paths[selected_index]


def get_line(file, remainder: list, width: int) -> tuple:
    """
    Reconstruct single line of the picture from PBM file.
    File type should be P1 - ASCII (plain).
    First 3 lines of the file should be read before the function call.

    Reads from the given file object and constructs a line with
    the specified width, considering any remaining characters from
    the previous call.

    Parameters:
    - file (file): The file object to read from.
    - remainder (list): A list containing characters left from
                        the previous call.
    - width (int): The desired width of the line.

    Returns:
    tuple: A tuple containing three elements:
        1. List of characters representing the constructed line.
        2. List of characters remaining after constructing the line.
        3. Boolean indicating if the end of the file is reached.
    """
    line = remainder[:]
    reached_end = False

    while len(line) < width:
        content = file.readline().rstrip().replace(' ', '')

        if content:
            for char_ in content:
                line.append(char_)
        else:
            reached_end = True
            break

    remainder = line[width:]
    line = line[:width]
    return line, remainder, reached_end


def get_range_args(line: list,
                   axis_position: int,
                   axis_step_: int = 1,
                   to_nearest: bool = True,
                   dot_value='1') -> tuple:
    """
    Determine how the line should be iterated - from firs dot_value
    to the last, or from the last dot_value to the first.

    Returns arguments for the 'range()' function - start, stop,
    and step.

    Args:
    - line (list): A list containing elements to search
                   for the dot value.
    - axis_position (int): The current position on the axis.
    - axis_step_ (int): Step by axis in degrees. (default: 1)
    - to_nearest (bool, optional): Flag to determine iteration direction
                                   (from nearest to farthest
                                   or allways from first to last).
                                   (default: True)
    - dot_value (optional): The value to search for within the line.
                            (default: '1')

    Returns:
    - Tuple[int, int, int]: A tuple representing
      the arguments for 'range()':
      - If dot_value is not found in the list, returns (0, 0, 1).
      - If iterating from nearest to farthest and dot_value found,
        returns (first_index, last_index + 1, 1) or
        (last_index, first_index - 1, -1), depends which index position
        is closer to axis_position.
      - If to_nearest is False and dot_value found,
        returns (first_index, last_index + 1, 1).
    """

    indices = [index for index, value in enumerate(line) if value == dot_value]
    if not indices:
        return 0, 0, 1
    first_index = indices[0]
    last_index = indices[-1]

    if to_nearest:

        distance_to_first = abs(axis_position - first_index * axis_step_)
        distance_to_last = abs(axis_position - last_index * axis_step_)

        if distance_to_first > distance_to_last:
            return last_index, first_index - 1, -1

    return first_index, last_index + 1, 1


def seconds_to_time(seconds: int, mode: str = 'hh:mm:ss') -> str:
    """
    Converts a given number of seconds into a specified time format.

    Args:
    - seconds (int): The number of seconds to be converted.
    - mode (str): The desired time format mode. (default: 'hh:mm:ss')
      Allowed modes are: 'mm:ss', 'hh:mm:ss', 'D.hh:mm:ss', 'hh:mm',
                         'D.hh:mm'.

    Returns:
    - str: A string representing the time in the specified format.

    Raises:
    - ValueError: If the provided mode is not one of the allowed modes.
    """

    valid_modes = ('mm:ss', 'hh:mm:ss', 'D.hh:mm:ss', 'hh:mm', 'D.hh:mm')
    if mode not in valid_modes:
        raise ValueError(
            "Invalid mode. Allowed modes are: {}".format(valid_modes)
        )

    days = hours = minutes = 0

    if 'D' in mode:
        days, seconds = divmod(seconds, 86400)  # 86400 sec in a day

    if 'hh' in mode:
        hours, seconds = divmod(seconds, 3600)  # 3600 sec in an hour

    # It is allways True. It is here in case valid_modes changes.
    if 'mm' in mode:
        minutes, seconds = divmod(seconds, 60)

    if seconds >= 30 and 'ss' not in mode:
        minutes += 1

    time_format = mode.replace('D', str(days))
    time_format = time_format.replace('hh', "{:02}".format(hours))
    time_format = time_format.replace('mm', "{:02}".format(minutes))
    time_format = time_format.replace('ss', "{:02}".format(seconds))

    return time_format


def show_info(common_info: str = '',
              preceding_info: str = '',
              following_info: str = '') -> None:
    """
    Display common_info on the hub light matrix
    and print combined information in console.

    Args:
    - common_info (str): The information to be displayed on the hub
                         and printed in console.
    - preceding_info (str): Information to be printed in console
                            before the common information.
    - following_info (str): Information to be printed in console
                            after the common information.

    Returns:
    - None
    """
    print(preceding_info + common_info + following_info)
    hub.display.show(common_info + ' ',
                     delay=500, wait=False,
                     loop=True, fade=4)


def error_warning(error_description, error_name: str, color=0) -> None:
    """
    Display error information based on the error type provided.

    Args:

    Returns:
    - None
    """
    color_dictionary = {'off': 0, 'pink': 1, 'violet': 2, 'blue': 3,
                        'turquoise': 4, 'light green': 5, 'green': 6,
                        'yellow': 7, 'orange': 8, 'red': 9, 'white': 10}
    if isinstance(color, str) and color in color_dictionary:
        hub.led(color_dictionary[color])
    elif isinstance(color, int):
        hub.led(color)
    elif isinstance(color, tuple):
        hub.led(*color)

    show_info(error_name, ' \n', ': {}'.format(str(error_description)))

    for _ in range(3):
        hub.sound.beep(131, 200, 3)
        wait_for_seconds(0.3)


def wait_until_tapped():
    """
    Display an animation until a tap gesture is detected.
    """
    animation = (hub.Image('00000:00000:00900:00000:00000:'),
                 hub.Image('00000:09990:09990:09990:00000:'),
                 hub.Image('00000:09990:09090:09990:00000:'),
                 hub.Image('00000:09990:09990:09990:00000:'),
                 hub.Image('00000:00000:00900:00000:00000:'),
                 hub.Image('00000:00000:00000:00000:00000:'))
    hub.display.show(animation, delay=600, wait=False, loop=True, fade=2)
    hub.sound.beep(131, 500, 0)
    print('Tap the hub to continue.')
    while hub.motion.gesture() != 0:
        continue
    hub.display.clear()


def calibration():
    animation = (hub.Image('00000:00000:90000:00000:00000:'),
                 hub.Image('00000:00000:99000:00000:00000:'),
                 hub.Image('00000:00000:99900:00000:00000:'),
                 hub.Image('00000:00000:99990:00000:00000:'),
                 hub.Image('00000:00000:99999:00000:00000:'),
                 hub.Image('00000:00000:09999:00000:00000:'),
                 hub.Image('00000:00000:00999:00000:00000:'),
                 hub.Image('00000:00000:00099:00000:00000:'),
                 hub.Image('00000:00000:00009:00000:00000:'),
                 hub.Image('00000:00000:00000:00000:00000:'))
    print('Calibration...\n'
          'Please wait, it may take a while.')
    hub.display.show(animation, delay=200, wait=False, loop=True, fade=2)

    pen.put_up()

    y_axis.calibrate_zero()

    x_axis.calibrate_zero()
    x_axis.calibrate_end()
    x_axis.go_home()

    if BACKLASH_CORRECTION:
        backlash_info = ('Backlash correction is applied. '
                         'Correction value is {} degrees.'. format(
                                x_axis.correction_step))
    else:
        backlash_info = 'Backlash correction is not applied.'

    print(' \nCalibration done.\n'
          'Dot diameter is {} mm\n'
          'X-axis step is {} degrees per dot\n'
          'Y-axis step is {} degrees per dot\n'
          '{}\n'
          'The width of the printing area is '
          '{} mm or {} dots'.format(DOT_DIMENSION,
                                    x_axis.step, y_axis.step,
                                    backlash_info,
                                    x_axis.length * DOT_DIMENSION,
                                    x_axis.length))

    x_axis.wait_until_motion_done()

    if WAIT_FOR_TAP_AFTER_CALIBRATION:
        wait_until_tapped()

    hub.display.clear()


def picture_dimensions(file) -> tuple:
    """
    Extracts the width and height dimensions
    from a PBM (Portable BitMap) file.

    Arguments:
    file (file): The PBM file object opened in read mode ('r').

    Returns:
    tuple: A tuple containing the width and height
           extracted from the file.

    Raises:
    RuntimeError: If there is an issue with the file format
                  or missing dimensions after comments.
    ValueError: If the extracted dimensions are invalid
                (negative or zero values).

    Note: Always use 'with' when open file.
    """
    line = '#'

    while line.startswith('#'):
        line = file.readline()

    try:
        width, height = map(int, line.split())
    except ValueError:
        raise RuntimeError(
            'Expected picture dimensions after comments in PBM-file.\n')

    if width < 1 or height < 1:
        raise ValueError(
            'Picture dimensions cannot be negative or 0.\n'
            'The problem line values: {}'.format(line))

    return width, height


def printing(image_path):
    animation = (hub.Image('90000:00000:00000:00000:00000:'),
                 hub.Image('99000:00000:00000:00000:00000:'),
                 hub.Image('99900:00000:00000:00000:00000:'),
                 hub.Image('99990:00000:00000:00000:00000:'),
                 hub.Image('99999:00000:00000:00000:00000:'),
                 hub.Image('99999:00009:00000:00000:00000:'),
                 hub.Image('99999:00099:00000:00000:00000:'),
                 hub.Image('99999:00999:00000:00000:00000:'),
                 hub.Image('99999:09999:00000:00000:00000:'),
                 hub.Image('99999:99999:00000:00000:00000:'),
                 hub.Image('99999:99999:90000:00000:00000:'),
                 hub.Image('99999:99999:99000:00000:00000:'),
                 hub.Image('99999:99999:99900:00000:00000:'),
                 hub.Image('99999:99999:99990:00000:00000:'),
                 hub.Image('99999:99999:99999:00000:00000:'),
                 hub.Image('99999:99999:99999:00009:00000:'),
                 hub.Image('99999:99999:99999:00099:00000:'),
                 hub.Image('99999:99999:99999:00999:00000:'),
                 hub.Image('99999:99999:99999:09999:00000:'),
                 hub.Image('99999:99999:99999:99999:00000:'),
                 hub.Image('99999:99999:99999:99999:90000:'),
                 hub.Image('99999:99999:99999:99999:99000:'),
                 hub.Image('99999:99999:99999:99999:99900:'),
                 hub.Image('99999:99999:99999:99999:99990:'),
                 hub.Image('99999:99999:99999:99999:99999:'),
                 hub.Image('99999:99999:99999:99999:00000:'),
                 hub.Image('99999:99999:99999:00000:00000:'),
                 hub.Image('99999:99999:00000:00000:00000:'),
                 hub.Image('99999:00000:00000:00000:00000:'),
                 hub.Image('00000:00000:00000:00000:00000:'))

    hub.display.show(animation, delay=1000, wait=False, loop=True, fade=2)
    with open(image_path, 'r') as picture:
        next(picture)
        picture_width, _ = picture_dimensions(picture)

        if picture_width > x_axis.length:
            raise RuntimeError(
                'Picture is too width.\n'
                'You are trying to print a picture that is '
                '{pic_width} pixels wide,\n'
                'but the printer can only print images '
                'that are {print_width} pixels wide.\n'
                'Resize current picture, '
                'try to decrease the DOT_DIMENSION constant,\n'
                'or try another picture.'.format(
                    pic_width=picture_width,
                    print_width=x_axis.length)
            )

        print(' \nPrinting...')

        rest_of_line = []
        while True:
            line, rest_of_line, end_of_picture = get_line(picture,
                                                          rest_of_line,
                                                          picture_width)
            if end_of_picture:
                break
            line_start, line_end, direction = get_range_args(
                line, x_axis.get_position(), x_axis.step, SHORTEST_PATH)

            y_axis.wait_until_motion_done()

            for j in range(line_start, line_end, direction):
                if line[j] == '1':
                    x_axis.run_to_position(j, True, 'steps')
                    pen.put_dot()

            y_axis.move_steps(1)

    hub.display.clear()
    x_axis.go_home()
    y_axis.go_home()


# The main program:
hub.display.align(2)

pen = Pen(PEN_MOTOR, PEN_DRAWS, PEN_DOESNT_DRAW, PEN_SPEED)
x_axis = Axis(X_MOTOR, X_GEAR_RATIO, X_WHEEL_DIAMETER, DOT_DIMENSION, X_SPEED,
              1, X_SENSOR, (X_ZERO_COLOR, X_ZERO_COLOR_2), X_END_COLOR,
              BACKLASH_CORRECTION, CORRECTION_VALUE)
y_axis = Axis(Y_MOTOR, Y_GEAR_RATIO, Y_WHEEL_DIAMETER, DOT_DIMENSION, Y_SPEED,
              1)

printing_timer = Timer()

try:
    _, slot_path = select_slot(ALLOW_TO_SELECT_SLOT, SLOT_TO_PRINT)
except RuntimeError as error:
    error_warning(error, 'NO SLOTS', 'red')
except ValueError as error:
    error_warning(error, 'INCORRECT SLOT', 'orange')
else:
    calibration()
    printing_timer.reset()

    try:
        printing(slot_path)
    except (RuntimeError, ValueError) as error:
        if str(error).startswith('Picture is too width'):
            error_warning(error, 'WIDTH ERROR', 'yellow')
        elif (str(error).startswith(
                'Picture dimensions cannot be negative or 0')
              or str(error).startswith(
                    'Expected picture dimensions after comments')):
            error_warning(error, 'INVALID FILE', 'pink')
        else:
            error_warning(error, 'ANOTHER ERROR', (255, 0, 255))
    else:
        hub.led(6)  # green
        show_info(seconds_to_time(printing_timer.now()),
                  ' \nPrinting completed in ')
