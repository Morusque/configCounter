
// put midi files in a folder (or subfolders) named data located next to this file

import javax.sound.midi.*;
import java.io.File;
import java.util.ArrayList;
import java.util.Collections;

ArrayList<Note> notes = new ArrayList<Note>();

int[] pitchClass = new int[12];

int[] configsCount = new int[57];
int[] sureConfigsCount = new int[57];

ArrayList<Chord> chords = new ArrayList<Chord>();

int[] numberOfConfigs = new int[57];

int[] numberOfCombinedConfigs = new int[57];
int[] numberOfSureCombinedConfigs = new int[57];

int[] numberOfSimultaneousPitchClasses = new int[13];

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
  for (int i=0;i<numberOfConfigs.length;i++) numberOfConfigs[i]=0;
  for (int i=0;i<numberOfCombinedConfigs.length;i++) numberOfCombinedConfigs[i]=0;
  for (int i=0;i<numberOfSureCombinedConfigs.length;i++) numberOfSureCombinedConfigs[i]=0;
  for (int i=0;i<numberOfSimultaneousPitchClasses.length;i++) numberOfSimultaneousPitchClasses[i]=0;
  // Process all MIDI file found in the data folder
  for (String file : files) {
    println("Processing: " + file);
    notes.clear();
    chords.clear();
    processMidiFile(new File(file));
    // count cumulative pitch classes and configurations
    count();
    buildChordsFromNotes();
    // populate numberOfSimultaneousPitchClasses based on chords
    for (int i=0;i<chords.size();i++) numberOfSimultaneousPitchClasses[chords.get(i).numberOfPitchClassesPresent]++;
    countValidConfigs();
    countCombinedConfigs();
  }
  // print the number of simultaneous pitch classes
  println("Simultaneous pitch classes:");
  for (int i=0; i<numberOfSimultaneousPitchClasses.length; i++) {
    println(nf(i, 2)+" : "+numberOfSimultaneousPitchClasses[i]);
  }  
  // print the configuration modes count
  println("Configuration modes count:");
  for (int i=0; i<configsCount.length; i++) {
    println(nf(i, 2)+" : "+configsCount[i]);
  }
  // print the sure configuration modes count
  println("Sure configuration modes count:");
  for (int i=0; i<sureConfigsCount.length; i++) {
    println(nf(i, 2)+" : "+sureConfigsCount[i]);
  }
  // print the number of configurations found
  println("Number of configurations found:");
  for (int i=0; i<numberOfConfigs.length; i++) {
    println(nf(i, 2)+" : "+numberOfConfigs[i]);
  }
  // print the number of configurations found
  println("Number of combined configurations found:");
  for (int i=0; i<numberOfCombinedConfigs.length; i++) {
    println(nf(i, 2)+" : "+numberOfCombinedConfigs[i]);
  }
  println("Number of sure combined configurations found:");
  for (int i=0; i<numberOfSureCombinedConfigs.length; i++) {
    println(nf(i, 2)+" : "+numberOfSureCombinedConfigs[i]);
  }
  exit();
}

void draw() {
}

void buildChordsFromNotes() {
  ArrayList events = new ArrayList();

  // Crée les événements de début et de fin
  for (int i = 0; i < notes.size(); i++) {
    Note n = (Note) notes.get(i);
    if (n.channel ==10) { // Ignore channel 10 (drums)
      continue;
    }
    events.add(new Event(n.startTick, true, n));
    events.add(new Event(n.stopTick, false, n));
  }

  // Tri manuel des événements (tri à bulles pour compatibilité maximale)
  for (int i = 0; i < events.size(); i++) {
    for (int j = i + 1; j < events.size(); j++) {
      Event ei = (Event) events.get(i);
      Event ej = (Event) events.get(j);
      if (ej.time < ei.time) {
        events.set(i, ej);
        events.set(j, ei);
      }
    }
  }

  ArrayList activeNotes = new ArrayList();
  float lastTime = -1;

  for (int i = 0; i < events.size(); i++) {
    Event e = (Event) events.get(i);

    if (e.time != lastTime && activeNotes.size() > 0) {
      Chord chord = new Chord();
      for (int j = 0; j < activeNotes.size(); j++) {
        chord.addNote((Note) activeNotes.get(j));
      }
      chords.add(chord);
    }

    if (e.isNoteOn) {
      if (!activeNotes.contains(e.note)) activeNotes.add(e.note);
    } else {
      activeNotes.remove(e.note);
    }

    lastTime = e.time;
  }
}

// Classe Event
class Event {
  float time;
  boolean isNoteOn;
  Note note;

  Event(float time, boolean isNoteOn, Note note) {
    this.time = time;
    this.isNoteOn = isNoteOn;
    this.note = note;
  }
}

void countValidConfigs() {

  for (int i = 0; i < chords.size(); i++) {
    Chord chord = (Chord) chords.get(i);
    int configsFound = 0;
    for (int n = 0; n < 57; n++) {
      if (chord.possibleModes[n]) {
        configsCount[n]++;
        // count number of true values in this config
        int notesInConfig = 0;
        for (int j = 0; j < 12 ; j++) if (classicalModes[n][j]) notesInConfig++;
        if (chord.numberOfPitchClassesPresent == notesInConfig) {
          sureConfigsCount[n]++;
          if (n==42) {
            println("42 HERE ! chord : "+i+" / "+chords.size());
          }
        }
        configsFound++;
      }
    }
    numberOfConfigs[configsFound]++;
  }

}

void countCombinedConfigs() {
  int N = chords.size();
  int[] dp = new int[N + 1]; // min number of segments from i to end
  int[] nextBreak = new int[N]; // where to go next in optimal path
  boolean[][] combinedCache = new boolean[N][12]; // store the union of chords[i..j]

  for (int i = 0; i <= N; i++) dp[i] = Integer.MAX_VALUE;
  dp[N] = 0;

  // process from end to start
  for (int i = N - 1; i >= 0; i--) {
    boolean[] combined = new boolean[12];
    for (int k = 0; k < 12; k++) combined[k] = false;

    for (int j = i + 1; j <= N; j++) {
      // combine chords i to j-1
      for (int k = 0; k < 12; k++) {
        combined[k] = combined[k] || chords.get(j - 1).pitchClasses[k] > 0;
      }

      // check compatibility
      boolean compatible = false;
      for (int m = 0; m < 57; m++) {
        if (isCompatible(combined, classicalModes[m])) {
          compatible = true;
          break;
        }
      }

      if (!compatible) break; // stop here

      // if segment [i..j-1] is valid, try using it
      if (dp[j] + 1 < dp[i]) {
        dp[i] = dp[j] + 1;
        nextBreak[i] = j;
        // clone combined notes for later analysis
        for (int k = 0; k < 12; k++) {
          combinedCache[i][k] = combined[k];
        }
      }
    }
  }

  // follow optimal path and count matching modes
  int i = 0;
  while (i < N && nextBreak[i] > i) {
    boolean[] combined = combinedCache[i];

    for (int m = 0; m < 57; m++) {
      if (isCompatible(combined, classicalModes[m])) {
        numberOfCombinedConfigs[m]++;
        if (isSame(combined, classicalModes[m])) {
          numberOfSureCombinedConfigs[m]++;
        }
      }
    }

    i = nextBreak[i];
  }
}

boolean isSame(boolean[] chord, boolean[] mode) {
  for (int i=0;i<chord.length;i++) if (chord[i]!=mode[i]) return false;
  return true;
}

boolean isCompatible(boolean[] chord, boolean[] mode) {
  for (int i=0;i<chord.length;i++) if (chord[i]) if (!mode[i]) return false;
  return true;
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
  /*
  for (int i = 0; i < pitchClass.length; i++) {
    println("Pitch class " + i + ": " + pitchClass[i]);
  }
  */
}

class Chord {
  ArrayList<Note> notes = new ArrayList<Note>();
  boolean[] possibleModes = new boolean[57];
  int[] pitchClasses = new int[12];
  int numberOfPitchClassesPresent = 0;

  Chord() {
    for (int i=0; i< possibleModes.length; i++) possibleModes[i] = true;
    for (int i=0; i< pitchClasses.length; i++) pitchClasses[i] = 0;
  }

  void addNote(Note note) {
    // add the note to the chord
    notes.add(note);

    // add note to pitchClasses
    int pitch = note.note % 12; // Get the pitch class (0-11)
    if (pitchClasses[pitch] == 0) {
      numberOfPitchClassesPresent++;
    }
    pitchClasses[pitch]++;

    // check if the note is in the mode
    for (int j = 0; j < classicalModes.length; j++) {
      if (possibleModes[j]) {
        if (!classicalModes[j][note.note % 12]) {
          // this mode is not possible anymore
          possibleModes[j] = false;
        }
      }
    }
  }
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
