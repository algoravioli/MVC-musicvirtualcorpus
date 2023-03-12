# %%
from PIL import Image, ImageDraw
import numpy as np

# import helper functions
from genere.helperfunctions import papersizefunctions
from genere.helperfunctions import drawmanuscriptlines
from genere.helperfunctions import createcanvas
from genere.helperfunctions import notationplacer_helper_dictionary

import os

from genere.helperfunctions.drawmanuscriptlines import (
    GLOBAL_MARGINS,
    GLOBAL_STAFF_MARGINS,
    GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS,
    GLOBAL_LINE_THICKNESS,
    GLOBAL_INDENTATION_IN_PIXELS,
)


class notationPlacer:
    def __init__(self, canvas, staffLineCoords):
        # currently only works if you don't change margins
        self.notePostionsVerticalRatios = notationplacer_helper_dictionary.generateNotationHelperDictionaryFromGlobalMargins(
            canvas,
            GLOBAL_MARGINS=GLOBAL_MARGINS,
            GLOBAL_STAFF_MARGINS=GLOBAL_STAFF_MARGINS,
            GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS=GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS,
            GLOBAL_LINE_THICKNESS=GLOBAL_LINE_THICKNESS,
        )  # returns dictionary with entries eg ["-C#"] = positionFraction, accidental, number of ledger lines, above_or_blow
        self.staffLineCoords = staffLineCoords
        self.placedNotes = {}  # this will be in [system, x, y] format
        self.numberOfPlacedNotes = 0

    def applyNoteheadAtCoord(self, canvas, x_left, y_top):
        notehead = Image.open("genere/images/notehead_small.png")
        notehead = notehead.resize(
            (
                int(10 + (0.5 * (GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS - 8))),
                int(10 + (0.5 * (GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS - 8))),
            )
        )
        canvas2 = canvas.copy()
        canvas2.paste(notehead, (x_left, y_top), notehead)
        return canvas2

    def drawLedgerLines(self, canvas, start_x, start_y, ledgerLineLength=17):
        drawer = ImageDraw.Draw(canvas)
        drawer.line(
            (
                start_x,
                start_y,
                start_x + ledgerLineLength,
                start_y,
            ),
            fill=(0, 0, 0),
            width=GLOBAL_LINE_THICKNESS,
        )
        return canvas

    def takeVerticalRatioAndReturnYVal(self, ratio, systemCoords):
        y_above = systemCoords[0][1]
        y_below = systemCoords[1][1]
        # below > above
        # thus, below - above is the height of staff lines
        # ratio * this difference
        position = (ratio * (y_below - y_above)) + y_above
        return position

    def midiNoteToMVCname(self, midiNoteNumber, sharp_or_flat):
        minMidiNumber = 48
        maxMidiNumber = 92
        if midiNoteNumber > maxMidiNumber:
            raise ValueError(
                "midiNoteNumber is too high. Only values between 48 to 92 are supported by this feature. If you want a higher value, please implement it yourself and delete this error."
            )

        if midiNoteNumber < minMidiNumber:
            raise ValueError(
                "midiNoteNumber is too low. If you are using bass clef, please check that the bass clef property/function you are using is properly enabled. Or else, please implement it yourself and delete this error."
            )

        chromaticScaleFlat = [
            "C",
            "Db",
            "D",
            "Eb",
            "E",
            "F",
            "Gb",
            "G",
            "Ab",
            "A",
            "Bb",
            "B",
        ]
        chromaticScaleSharp = [
            "C",
            "C#",
            "D",
            "D#",
            "E",
            "F",
            "F#",
            "G",
            "G#",
            "A",
            "A#",
            "B",
        ]

        midiNoteNumber_pitchClass = midiNoteNumber % 12
        if sharp_or_flat == "sharp":
            pitchName = chromaticScaleSharp[midiNoteNumber_pitchClass]
        elif sharp_or_flat == "flat":
            pitchName = chromaticScaleFlat[midiNoteNumber_pitchClass]
        else:
            raise ValueError(
                "Variable input sharp_or_flat must be a string that is either 'sharp' or 'flat'."
            )

        octave = midiNoteNumber // 12
        if octave == 4:
            pitchClass = "-" + pitchName
        elif octave == 5:
            pitchClass = pitchName
        elif octave == 6:
            pitchClass = "+" + pitchName
        elif octave == 7:
            pitchClass = "++" + pitchName

        return str(pitchClass)

    def transparentPaste(
        self, foreground_image, background_image, alpha=1.0, box=(0, 0)
    ):
        if foreground_image.mode != "RGBA":
            foreground_image = foreground_image.convert("RGBA")
        foreground_image_transparent = Image.new("RGBA", foreground_image.size)
        foreground_image_transparent = Image.blend(
            foreground_image_transparent, foreground_image, alpha
        )
        background_image.paste(
            foreground_image_transparent, box, foreground_image_transparent
        )
        return background_image

    def applyAccidental(self, canvas, sharp_or_flat, start_x, start_y):
        if sharp_or_flat == "sharp":
            accidental = Image.open("genere/images/sharp_small.png")
            accidental = accidental.resize((12, 19))
            canvas2 = canvas.copy()
            canvas2 = self.transparentPaste(
                accidental, canvas, box=(start_x - 12, start_y - 4)
            )
        elif sharp_or_flat == "flat":
            accidental = Image.open("genere/images/flat_small.png")
            accidental = accidental.resize((9, 17))
            canvas2 = canvas.copy()
            canvas2 = self.transparentPaste(
                accidental, canvas, box=(start_x - 9, start_y - 6)
            )
        else:
            raise ValueError(
                "Variable input sharp_or_flat must be a string that is either 'sharp' or 'flat'."
            )

        return canvas2

    def applyNoteheadAt(
        self, canvas, which_system, percentage_horizontal, note, sharp_or_flat="sharp"
    ):
        if type(note) == int:
            note = self.midiNoteToMVCname(note, sharp_or_flat)
        elif type(note) == str:
            pass
        else:
            raise ValueError(
                'Variable input note must be either an integer or a string. If it is an integer, it must be a midi note number. If it is a string, it must be a string that is a valid note name in the MVC format (e.g "+C").'
            )
        # system starts from 0
        # fraction refers to the horizontal position of the bar
        system_number = which_system
        systemCoords = self.staffLineCoords[system_number]
        start_x = int(
            ((systemCoords[1][0] - systemCoords[0][0]) * percentage_horizontal)
            + systemCoords[0][0]
        )
        start_y = int(
            self.takeVerticalRatioAndReturnYVal(
                self.notePostionsVerticalRatios[note][0], systemCoords
            )
        )
        if "#" in note:
            canvas = self.applyAccidental(canvas, "sharp", start_x, start_y)
        elif "b" in note:
            canvas = self.applyAccidental(canvas, "flat", start_x, start_y)

        canvas, _ = drawmanuscriptlines.OneSetOfLines(
            canvas, systemCoords[0][0], systemCoords[0][1]
        )

        currentNoteAttributes = self.notePostionsVerticalRatios[note]
        # ledger lines
        if currentNoteAttributes[2] > 0:
            for i in range(currentNoteAttributes[2]):
                # check if note is above or below staff
                if "below" in currentNoteAttributes:
                    multiplier = -1
                    canvas = self.drawLedgerLines(
                        canvas,
                        start_x - 4,
                        systemCoords[1][1]
                        - (
                            multiplier
                            * ((i + 1) * GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS)
                        ),
                    )
                elif "above" in currentNoteAttributes:
                    multiplier = 1
                    canvas = self.drawLedgerLines(
                        canvas,
                        start_x - 4,
                        (
                            systemCoords[0][1]
                            - (
                                multiplier
                                * ((i + 1) * GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS)
                            )
                        ),
                    )
                    # print((systemCoords[0][1] - (multiplier * ((i + 1) * 12))))

        # draw the note
        canvas = self.applyNoteheadAtCoord(canvas, start_x, start_y)
        self.placedNotes[self.numberOfPlacedNotes] = [
            system_number,
            note,
            start_x,
            start_y,
        ]
        self.numberOfPlacedNotes += 1

        return canvas

    def applyTrebleClef(self, canvas, which_system, on_all=False):
        system_number = which_system
        systemCoords = self.staffLineCoords[system_number]
        start_x = systemCoords[0][0] + 3
        start_y = systemCoords[0][1] - 18
        trebleClef = Image.open("genere/images/trebleclef.png")
        trebleClef = trebleClef.resize(
            (35, 70 + (5 * (GLOBAL_STAFF_INBETWEEN_SPACING_IN_PIXELS - 8)))
        )
        canvas2 = canvas.copy()
        canvas2 = self.transparentPaste(trebleClef, canvas, box=(start_x, start_y))

        if on_all:
            for i in range(len(self.staffLineCoords)):
                canvas = self.applyTrebleClef(canvas, i)

        return canvas2

    def applyTrebleClefAtCoord(self, canvas, x, y):
        trebleClef = Image.open("genere/images/trebleclef.png")
        trebleClef = trebleClef.resize((30, 30))
        canvas2 = canvas.copy()
        canvas2 = self.transparentPaste(trebleClef, canvas, box=(x, y))
        return canvas2


# %%
