import speech_recognition as sr
from difflib import SequenceMatcher
import pandas as pd
import random
import os
import librosa
import nltk
nltk.download('cmudict')
from nltk.corpus import cmudict
import requests
from io import BytesIO
import pygame

def speak(text):

  api_url = "https://api.streamelements.com/kappa/v2/speech"
  params = {
      'voice': 'Brian', 
      'text': text.strip()
  }

  response = requests.get(api_url, params=params) 

  if response.status_code == 200: 
    pygame.mixer.init()
    pygame.mixer.music.load(BytesIO(response.content))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
      pygame.time.Clock().tick(5)
  else:
    print(f"Error: {response.status_code}") 

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def extract_pitch(audio_path):
    y, sr = librosa.load(audio_path)
    pitches, magnitudes = librosa.core.piptrack(y=y, sr=sr)
    return pitches, magnitudes

def get_audio_duration(audio_path):
    y, sr = librosa.load(audio_path)
    duration = librosa.get_duration(y=y, sr=sr)
    return duration

def text_to_phonemes(text):
    # Use the CMU Pronouncing Dictionary from nltk
    d = cmudict.dict()
    words = text.lower().split()
    phonemes = []
    for word in words:
        if word in d:
            phonemes.extend(d[word][0])
        else:
            # If word is not in the dictionary, use the word itself as a fallback
            phonemes.append(word)
    return " ".join(phonemes)

def compare_phonemes(reference_phonemes, recognized_phonemes):
    matcher = SequenceMatcher(None, reference_phonemes, recognized_phonemes)
    differences = list(matcher.get_opcodes())
    return differences

def recognize_and_compare(reference_text, reference_med_pitch, reference_std_pitch):
    recognizer = sr.Recognizer()
    print()
    print("\t******************Welcome to ClearSpeak******************")
    print("\n\tReference Text:", reference_text)

    # Convert reference text to phonemes
    reference_phonemes = text_to_phonemes(reference_text)
    print("\tReference Phonemes:", reference_phonemes)
    print("\tExact pronouncation:")
    speak(reference_text)
    op = input("\tDo you want to hear again(y/n):")
    while(op == "y"):
        # op = input("Do you want to hear again(y/n):")
        if op== "y":
            speak(reference_text)
            op = input("\tDo you want to hear again(y/n):")

    # Record audio
    with sr.Microphone() as source:
        print("")
        input("\tPress Enter to Say...")
        print("")
        print("\tSay something...")
        audio = recognizer.listen(source, timeout=5)

    # Save audio to a temporary WAV file
    temp_wav_path = "temp.wav"
    with open(temp_wav_path, "wb") as temp_wav:
        temp_wav.write(audio.get_wav_data())

    try:
        
        # Perform speech recognition
        recognized_text = recognizer.recognize_google(audio)
        # print("You said:", recognized_text)

        # Extract pitch information from the recorded audio
        pitches, _ = extract_pitch(temp_wav_path)

        # Calculate similarity between recognized text and reference text
        similarity_score = similarity(recognized_text.lower(), reference_text.lower())
        

        # Adjust the threshold based on your desired strictness
        similarity_threshold = 0.95

        # Calculate absolute mean pitch difference
        abs_pitch_diff = abs(pitches.mean() - reference_med_pitch)

        # Adjust similarity based on absolute mean pitch difference
        if abs_pitch_diff > 10:
            similarity_reduction = 0.3
        elif abs_pitch_diff > 6:
            similarity_reduction = 0.2
        elif abs_pitch_diff > 4:
            similarity_reduction = 0.1
        else:
            similarity_reduction = 0.0

        # Apply similarity reduction
        similarity_score -= similarity_reduction

        # Calculate median and standard deviation for pitch
        med_pitch = librosa.hz_to_midi(librosa.midi_to_hz(pitches.mean()))
        std_pitch = librosa.hz_to_midi(librosa.midi_to_hz(pitches.std()))
        print("\tSimilarity Score:", round(similarity_score,2))
        # print("\tMedian Pitch:", med_pitch)
        # print("\tStandard Deviation of Pitch:", std_pitch)

        # Get the duration of the recorded audio
        duration = get_audio_duration(temp_wav_path)
        print("\tAudio Duration:", round(duration,2), "seconds")

        # Convert recognized text to phonemes
        recognized_phonemes = text_to_phonemes(recognized_text)
        print("\tRecognized Phonemes:", recognized_phonemes)

        # Compare phonemes and detect mistakes
        differences = compare_phonemes(reference_phonemes, recognized_phonemes)
        print("\tPhoneme Differences:", differences)

        # Check the final similarity score
        final_similarity_score = similarity_score 

        if final_similarity_score >= 0.8:
            print("\tExactly correct!")
        elif final_similarity_score >= 0.6:
            print("\tNearly correct!")
        elif final_similarity_score >= 0.4:
            print("\tSlightly correct.")
        else:
            print("\tWrong.")

    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
    finally:
        # Remove the temporary WAV file
        os.remove(temp_wav_path)

if __name__ == "__main__":
    # Load the dataset from Excel
    excel_file_path = r"dataset2 (1).xlsx"
    df = pd.read_excel(excel_file_path)

    # Check if the DataFrame has at least one row and 'med_pitch' column
    if not df.empty and 'mean_pitch' in df.columns:
        while True:
        # Select a random row from the dataset
            random_row = df.sample(1)

        # Get the reference text and pitch values from the selected row
            reference_text = random_row['spelling'].values[0]
            reference_med_pitch = random_row['mean_pitch'].values[0]
            reference_std_pitch = random_row['std_pitch'].values[0]

        # Call the function with the randomly selected reference text and pitch values
            recognize_and_compare(reference_text, reference_med_pitch, reference_std_pitch)
            num = int(input("Do you Want to Continue?(1 for yes 0 for no)"))
            if num == 0:
                break
    else:
        print("The DataFrame is empty or does not have the 'med_pitch' column.")
