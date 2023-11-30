"""
Examples of using functions out of context:
- two_digits_image
- select_on_display
- get_slot_path
- select_slot
"""
import hub


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
    - This function assumes that the hub library has been imported.
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
                  check_word: str = '') -> str:
    """
    Retrieve the path associated with a given slot number
    from the 'projects/.slots' file.

    Args:
    - slot (int, optional): The slot number (0-19 inclusive) to retrieve
                            the path for (default: 0).
    - extension (str, optional): The file extension to append the path
                                (default: '.py').
    - do_check (bool, optional): Flag to indicate whether to perform
                                a file format check (default: False).
    - check_word (str, optional): The word used for file format checking
                                (default: empty string).

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
        slot_data = eval(slots_file.readline()).get(slot)
    if slot_data:
        path = 'projects/{}/__init__{}'.format(slot_data.get('id'), extension)

        # open() can reach OSError, if the file extension is different
        # from the extension argument.
        with open(path) as file:
            if file.readline().split()[0] != check_word and do_check:
                raise RuntimeError('File format check failed.')
        return path
    else:
        raise RuntimeError('Slot {} is empty.\nTry to upload file again, '
                           'or try another slot.'.format(slot))


def select_slot(let_select: bool = True, default_slot: int = 0,
                check_file: bool = False, word_to_check: str = '') -> tuple:
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
            path = get_slot_path(i, do_check=check_file,
                                 check_word=word_to_check)
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


# Examples of usage:
print('Getting slot path from the slot #0 directly '
      'and printing the file data:\n \n')
# Get slot path from the slot #0 directly:
slot_number = 0
path = get_slot_path(slot_number)
with open(path, 'r') as file:
    for line in file:
        print(line)

print(' \n \n')

print('Selecting slot from all available slots on the hub '
      'and printing file data:\n \n')
# Select from all available slots on the hub:
slot, path = select_slot()
with open(path, 'r') as file:
    for line in file:
        print(line)

print(' \n \n')

print('Selecting value from the range [0-100]:\n \n')
# Select value from the range [0-100]:
value = select_on_display(range(100))
print(value)

print(' \n \n')

print('Selecting value from custom tuple of values:\n \n')
# Select value from custom tuple of values:
custom_range = ('1', '11', '21', 2, 12, 22, 1000, '100', 3.14, 'word')
value = select_on_display(custom_range)
print(value)

print(' \n \n')

print('Selecting value from a string:\n \n')
# Select value from a string:
string = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890.,:;!?"~`#$%<^>&*()-+_=[]{}/|\@'
value = select_on_display(string)
print(value)

print(' \n \n')

print('Showing two digits value on the display in special font.')
# Show two digits value on the display in special font:
value_to_show = 42
hub.display.show(two_digits_image(value_to_show))
