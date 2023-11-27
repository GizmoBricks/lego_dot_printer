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
