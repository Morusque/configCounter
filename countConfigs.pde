
// put midi files in a folder (or subfolders) named data located next to this file

import javax.sound.midi.*;
import java.io.File;
import java.util.ArrayList;

ArrayList<Note> notes = new ArrayList<Note>();

int[] pitchClass = new int[12];

int[] configsCount = new int[57];

void setup() {
  size(400, 400);
  ArrayList<String> files = new ArrayList<String>();
  // add all files from dataPath() including subfolders
  File[] filesArray = new File(dataPath("")).listFiles();
  for (File file : filesArray) {
    if (file.isDirectory()) {
      File[] subFiles = file.listFiles();
      for (File subFile : subFiles) {
        if (subFile.getName().endsWith(".mid")) {
          files.add(subFile.getAbsolutePath());
        }
      }
    } else if (file.getName().endsWith(".mid")) {
      files.add(file.getAbsolutePath());
    }
  }
  // Process all MIDI file found in the data folder
  for (String file : files) {
    println("Processing: " + file);
    notes.clear();
    processMidiFile(new File(file));
    // count cumulative pitch classes and configurations
    count();
  }
  exit();
}

void draw() {
}

void count() {
  notes.sort((a, b) -> Integer.compare(a.startTick, b.startTick));
  for (Note note : notes) {
    if (note.channel ==10) { // Ignore channel 10 (drums)
      continue;
    }
    int pitch = note.note % 12; // Get the pitch class (0-11)
    pitchClass[pitch]++;
  }
  for (int i = 0; i < pitchClass.length; i++) {
    println("Pitch class " + i + ": " + pitchClass[i]);
  }
  boolean[] possibleModes = new boolean[57];
  for (int i=0; i< possibleModes.length; i++) possibleModes[i] = true;
  // go through the notes chronologically
  for (int i = 0; i < notes.size(); i++) {
    Note note = notes.get(i);
    if (note.channel == 10) { // Ignore channel 10 (drums)
      continue;
    }
    // go through all the modes
    boolean[] nextPossibleModes = new boolean[57];// possible modes including the next note
    boolean[] newPossibleModes = new boolean[57];// possible modes cleared and starting from the next note
    for (int k = 0; k < 57; k++) nextPossibleModes[k] = possibleModes[k];
    for (int k = 0; k < 57; k++) newPossibleModes[k] = true;
    for (int j = 0; j < classicalModes.length; j++) {
      if (possibleModes[j]) {
        // check if the note is in the mode
        if (!classicalModes[j][note.note % 12]) {
          // this mode is not possible anymore
          nextPossibleModes[j] = false;
          newPossibleModes[j] = false;
        }
      }
    }
    int numberOfPossibleModes = 0;
    for (int j = 0; j < nextPossibleModes.length; j++) {
      if (nextPossibleModes[j]) numberOfPossibleModes++;
    }
    // if there is still at least one possible mode in the new list, copy the new list into the actual list
    if (numberOfPossibleModes > 0) {
        possibleModes = nextPossibleModes;
    } else {
      // if there is no possible mode anymore, add the last possible modes to the count
      for (int j = 0; j < possibleModes.length; j++) {
        if (possibleModes[j]) configsCount[j]++;
      }
      // reset the list to the current state
      possibleModes = newPossibleModes;
    }
    // if it's the last note of the track, add the last possible modes to the count
    if (i == notes.size() - 1) {
      for (int j = 0; j < possibleModes.length; j++) {
        if (possibleModes[j]) configsCount[j]++;
      }
    }
  }
  // print the configuration modes count
  println("Configuration modes count:");
  for (int i=0; i<configsCount.length; i++) {
    print(nf(i, 2)+" : "+configsCount[i]+" | ");
    if (i % 6 == 5) println("");
  }
  println("");
}

void processMidiFile(File midiFile) {
  try {
    Sequence sequence = MidiSystem.getSequence(midiFile);
    for (Track track : sequence.getTracks()) {
      processTrack(track);
    }
  }
  catch (Exception e) {
    e.printStackTrace();
  }
}

void processTrack(Track track) {
  for (int i = 0; i < track.size(); i++) {
    MidiEvent event = track.get(i);
    MidiMessage message = event.getMessage();

    if (message instanceof ShortMessage) {
      ShortMessage sm = (ShortMessage) message;
      long tick = event.getTick();  // Get the tick time of the event

      if (sm.getCommand() == ShortMessage.NOTE_ON) {
        int note = sm.getData1();
        int velocity = sm.getData2();

        if (velocity > 0) {
          // Create and add the Note object to the ArrayList
          notes.add(new Note(note, velocity, sm.getChannel(), tick, -1)); // stopTick is -1 for now
        } else {
          // Handle NOTE_OFF using a NOTE_ON with velocity 0
          closeNote(note, tick);
        }
      } else if (sm.getCommand() == ShortMessage.NOTE_OFF) {
        int note = sm.getData1();
        closeNote(note, event.getTick());
      }
    }
  }
}

void closeNote(int noteValue, long stopTick) {
  for (Note note : notes) {
    if (note.note == noteValue && note.stopTick == -1) {
      note.stopTick = (int) stopTick; // Update stopTick when the note is released
      break;
    }
  }
}

class Note {
  int note;
  int velocity;
  int channel;
  int startTick;
  int stopTick;
  int layer = -1;

  Note(int note, int velocity, int channel, long startTick, long stopTick) {
    this.note = note;
    this.velocity = velocity;
    this.channel = channel;
    this.startTick = (int) startTick;
    this.stopTick = (int) stopTick;
  }
}

boolean[][] classicalModes = new boolean[][]{

  // Major Scale
  {true, false, true, false, true, true, false, true, false, true, false, true},
  {false, true, false, true, true, false, true, false, true, false, true, true},
  {true, false, true, true, false, true, false, true, false, true, true, false},
  {false, true, true, false, true, false, true, false, true, true, false, true},
  {true, true, false, true, false, true, false, true, true, false, true, false},
  {true, false, true, false, true, false, true, true, false, true, false, true},
  {false, true, false, true, false, true, true, false, true, false, true, true},
  {true, false, true, false, true, true, false, true, false, true, true, false},
  {false, true, false, true, true, false, true, false, true, true, false, true},
  {true, false, true, true, false, true, false, true, true, false, true, false},
  {false, true, true, false, true, false, true, true, false, true, false, true},
  {true, true, false, true, false, true, true, false, true, false, true, false},

  // Melodic Major Scale
  {true, false, true, false, true, true, false, true, true, false, true, false},
  {false, true, false, true, true, false, true, true, false, true, false, true},
  {true, false, true, true, false, true, true, false, true, false, true, false},
  {false, true, true, false, true, true, false, true, false, true, false, true},
  {true, true, false, true, true, false, true, false, true, false, true, false},
  {true, false, true, true, false, true, false, true, false, true, false, true},
  {false, true, true, false, true, false, true, false, true, false, true, true},
  {true, true, false, true, false, true, false, true, false, true, true, false},
  {true, false, true, false, true, false, true, false, true, true, false, true},
  {false, true, false, true, false, true, false, true, true, false, true, true},
  {true, false, true, false, true, false, true, true, false, true, true, false},
  {false, true, false, true, false, true, true, false, true, true, false, true},

  // Harmonic Major Scale
  {true, false, true, false, true, true, false, true, true, false, false, true},
  {false, true, false, true, true, false, true, true, false, false, true, true},
  {true, false, true, true, false, true, true, false, false, true, true, false},
  {false, true, true, false, true, true, false, false, true, true, false, true},
  {true, true, false, true, true, false, false, true, true, false, true, false},
  {true, false, true, true, false, false, true, true, false, true, false, true},
  {false, true, true, false, false, true, true, false, true, false, true, true},
  {true, true, false, false, true, true, false, true, false, true, true, false},
  {true, false, false, true, true, false, true, false, true, true, false, true},
  {false, false, true, true, false, true, false, true, true, false, true, true},
  {false, true, true, false, true, false, true, true, false, true, true, false},
  {true, true, false, true, false, true, true, false, true, true, false, false},

  // Harmonic Minor Scale
  {true, false, true, true, false, true, false, true, true, false, false, true},
  {false, true, true, false, true, false, true, true, false, false, true, true},
  {true, true, false, true, false, true, true, false, false, true, true, false},
  {true, false, true, false, true, true, false, false, true, true, false, true},
  {false, true, false, true, true, false, false, true, true, false, true, true},
  {true, false, true, true, false, false, true, true, false, true, true, false},
  {false, true, true, false, false, true, true, false, true, true, false, true},
  {true, true, false, false, true, true, false, true, true, false, true, false},
  {true, false, false, true, true, false, true, true, false, true, false, true},
  {false, false, true, true, false, true, true, false, true, false, true, true},
  {false, true, true, false, true, true, false, true, false, true, true, false},
  {true, true, false, true, true, false, true, false, true, true, false, false},
  
  // Augmented Scale
  {true, false, false, true, true, false, false, true, true, false, false, true},
  {false, false, true, true, false, false, true, true, false, false, true, true},
  {false, true, true, false, false, true, true, false, false, true, true, false},
  {true, true, false, false, true, true, false, false, true, true, false, false},

  // Half-Whole Diminished Scale
  {true, true, false, true, true, false, true, true, false, true, true, false},
  {true, false, true, true, false, true, true, false, true, true, false, true},
  {false, true, true, false, true, true, false, true, true, false, true, true},

  // Whole Tone Scale
  {true, false, true, false, true, false, true, false, true, false, true, false},
  {false, true, false, true, false, true, false, true, false, true, false, true}
};
