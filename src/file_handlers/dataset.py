# Mark Evers
# Created: 3/30/2018
# dataset.py
# Functions for getting the data set

import os
import pandas as pd
import pickle
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.model_selection import train_test_split

from src.globals import *
from src.midi_handlers.midi_file import MidiFileText, MidiTrackText, MidiFileNHot, MidiFileNHotTimeSeries



class VectorGetter:

    def __init__(self, base_dir, file_converter):
        self.base_dir = base_dir
        self.file_converter = file_converter
        self.meta_df = None
        self.composers = None
        self.n_composers = 0
        self.X_filenames = None
        self.y_filenames = None
        self.X_train_filenames = None
        self.y_train_filenames = None
        self.X_test_filenames = None
        self.y_test_filenames = None
        self.last_train_chunk_i = 0
        self.last_test_chunk_i = 0
        self.n_train_files = 0
        self.n_test_files = 0

        self.y_label_encoder = None
        self.y_onehot_encoder = None

        self.get_meta_df()
        self.get_composers()
        self.get_filenames()



    def reset_chunks(self):
        self.last_train_chunk_i = 0
        self.last_test_chunk_i = 0




    def get_meta_df(self, csv_file = "meta.csv"):
        """
        Gets a meta dataframe with the proper schema from <dir>.

        :param csv_file: The name of the csv file.
        :return: A pandas dataframe with the metadate.
        """
        self.meta_df = pd.read_csv(os.path.join(self.base_dir, csv_file), index_col="filename")
        self.meta_df = self.meta_df[self.meta_df.type == 1]
        return self.meta_df



    def get_composers(self):
        """
        Returns a list of composers that have at least MINIMUM_WORKS pieces.

        :return: A list of composers
        """

        if self.base_dir.startswith("midi/classical"):
            valid_composers = ["Bach", "Beethoven", "Chopin", "Debussy", "Giuliani", "Handel", "Hays", "Hewitt", "Mozart", "Paganini", "Scarlatti", "Schubert", "Sor", "Tchaikovsky", "Thomas", "Tucker", "Vivaldi", "Webster"]
        else:
            composers_df = pd.DataFrame(self.meta_df.groupby("composer").type.count())
            composers_df.columns = ["works"]
            valid_composers = composers_df[composers_df.works > MINIMUM_WORKS].index.values

        print("Found", len(valid_composers), "composers:", ", ".join(valid_composers))

        self.composers = valid_composers
        self.n_composers = len(self.composers)
        self.y_label_encoder = LabelEncoder().fit(self.composers)
        self.y_onehot_encoder = OneHotEncoder().fit(self.y_label_encoder.transform(self.composers).reshape(-1, 1))

        return valid_composers



    def get_filenames(self):
        """
        Gets a list of filenames for each composer and the appropriate label.

        :return: <list of tracks as text>, <list of labels>
        """
        self.X_filenames = []
        self.y_filenames = []

        for composer in self.composers:

            composers_works = self.meta_df[self.meta_df.composer == composer]
            if composers_works.composer.count() > MAXIMUM_WORKS:
                composers_works = composers_works.sample(MAXIMUM_WORKS)

            self.X_filenames.extend(composers_works.index.values)
            self.y_filenames.extend(composers_works.composer.values)


        self.X_train_filenames, self.X_test_filenames, self.y_train_filenames, self.y_test_filenames = train_test_split(self.X_filenames, self.y_filenames, stratify=self.y_filenames)
        self.n_train_files = len(self.X_train_filenames)
        self.n_test_files = len(self.X_test_filenames)
        print("Found", self.n_train_files, "training and", self.n_test_files, "test MIDI files!")


        return self.X_filenames, self.y_filenames



    def get_chunk(self, chunk_size, train_or_test):
        """
        Easy wrapper function to get all the docs and their labels

        :return: docs: list of docs, y: list of docs' labels, composers: list of composers, n_features: number of features
        """

        if train_or_test == "train":
            X_chunk_filenames = self.X_train_filenames[self.last_train_chunk_i:self.last_train_chunk_i + chunk_size]
            y_chunk_filenames = self.y_train_filenames[self.last_train_chunk_i:self.last_train_chunk_i + chunk_size]
        elif train_or_test == "test":
            X_chunk_filenames = self.X_test_filenames[self.last_test_chunk_i:self.last_test_chunk_i + chunk_size]
            y_chunk_filenames = self.y_test_filenames[self.last_test_chunk_i:self.last_test_chunk_i + chunk_size]
        else:
            raise ValueError("train_or_test must be either 'train' or 'test'.")

        X = []
        y = []

        complete = 0
        total = len(X_chunk_filenames)
        # print("\nLoading MIDI files...")
        progress_bar(complete, total)

        for filename, composer in zip(X_chunk_filenames, y_chunk_filenames):

            X_file = self.file_converter(filename, self.meta_df.loc[filename][MUSIC_NOTES]).to_X()
            X.extend(X_file)
            y.extend([composer] * len(X_file))

            complete += 1
            if train_or_test == "train":
                self.last_train_chunk_i += 1
                progress_bar(self.last_train_chunk_i, self.n_train_files)
            elif train_or_test == "test":
                self.last_test_chunk_i += 1
                progress_bar(self.last_test_chunk_i, self.n_test_files)



        y = self.y_label_encoder.transform(y).reshape(-1, 1)
        y = np.array(self.y_onehot_encoder.transform(y).todense(), dtype=np.byte)



        X = np.array(X, dtype=np.byte)
        # print(len(y), "individual tracks loaded!")

        return X, y



    def get_all(self):

        print("\nLoading MIDI files...")

        X = []
        y = []

        complete = 0
        total = len(self.X_filenames)
        progress_bar(complete, total)

        for filename, composer in zip(self.X_filenames, self.y_filenames):
            X_file = self.file_converter(filename, self.meta_df.loc[filename][MUSIC_NOTES]).to_X()
            X.extend(X_file)
            y.extend([composer] * len(X_file))

            complete += 1
            progress_bar(complete, total)

        y = self.y_label_encoder.transform(y).reshape(-1, 1)
        y = np.array(self.y_onehot_encoder.transform(y).todense(), dtype=np.byte)
        X = np.array(X, dtype=np.byte)
        return X, y




    def get_all_split(self):
        """
        Easy wrapper function to get all the docs and their labels

        :return: docs: list of docs, y: list of docs' labels, composers: list of composers, n_features: number of features
        """

        print("\nLoading MIDI files...")


        X_train = []
        X_test = []
        y_train = []
        y_test = []

        complete = 0
        total = len(self.X_filenames)
        progress_bar(complete, total)

        for filename, composer in zip(self.X_train_filenames, self.y_train_filenames):
            X_file = self.file_converter(filename, self.meta_df.loc[filename][MUSIC_NOTES]).to_X()
            X_train.extend(X_file)
            y_train.extend([composer] * len(X_file))

            complete += 1
            progress_bar(complete, total)

        for filename, composer in zip(self.X_test_filenames, self.y_test_filenames):
            X_file = self.file_converter(filename, self.meta_df.loc[filename][MUSIC_NOTES]).to_X()
            X_test.extend(X_file)
            y_test.extend([composer] * len(X_file))

            complete += 1
            progress_bar(complete, total)


        # get shuffled indexes
        shuffled_i = np.arange(len(X_train))
        np.random.shuffle(shuffled_i)

        X_train = np.array(X_train, dtype=np.byte)[shuffled_i]
        y_train = self.y_label_encoder.transform(y_train).reshape(-1, 1)
        y_train = np.array(self.y_onehot_encoder.transform(y_train).todense(), dtype=np.byte)[shuffled_i]

        X_test = np.array(X_test, dtype=np.byte)
        y_test = self.y_label_encoder.transform(y_test).reshape(-1, 1)
        y_test = np.array(self.y_onehot_encoder.transform(y_test).todense(), dtype=np.byte)
        return X_train, X_test, y_train, y_test




class VectorGetterText(VectorGetter):

    def __init__(self, base_dir="raw_midi"):
        super().__init__(base_dir, MidiFileText)

        self.vectorizer_pickle = os.path.join(self.base_dir, "text_vectorizer.pkl")
        self.vectorizer = None
        self.n_features = 0


        self.get_vectorizer()



    @staticmethod
    def tokenize(text):
        """
        Simple tokenize function to be used in the CountVectorizer
        :param text: The text to be tokenized
        :return: A list of tokens
        """
        return text.split(" ")



    def get_vectorizer(self):

        if os.path.exists(self.vectorizer_pickle):
            print("Loading vectorizer from", self.vectorizer_pickle, "...")
            with open(self.vectorizer_pickle, "rb") as f:
                self.vectorizer = pickle.load(f)
        else:
            self.train_vectorizer()

        self.n_features = len(self.vectorizer.get_feature_names())
        MidiTrackText.vectorizer = self.vectorizer
        print("Loaded a vocabulary of", self.n_features, "features.")



    def train_vectorizer(self):

        print("Learning vocabulary...")
        vocab = set()

        df = self.meta_df[self.meta_df.composer.isin(self.composers)]

        i = 0
        total = df.index.size
        for file in df.index.values:
            mid = MidiFileText(file, self.meta_df)
            text = mid.to_text()

            for track in text:
                vocab.update(track)

            i += 1
            progress_bar(i, total)

        vocab = list(vocab)

        print("Fitting vectorizer...")
        self.vectorizer = CountVectorizer(tokenizer=VectorGetterText.tokenize, max_features=TEXT_MAXIMUM_FEATURES, dtype=np.byte).fit(
            vocab)

        print("Saving", self.vectorizer_pickle, "...")
        with open(self.vectorizer_pickle, "wb") as f:
            pickle.dump(self.vectorizer, f)




class VectorGetterNHot(VectorGetter):

    def __init__(self, base_dir="midi"):
        super().__init__(base_dir, MidiFileNHot)
        self.n_features = 128 + len(DURATION_BINS) + 4



class VectorGetterNHotTimeSeries(VectorGetter):

    def __init__(self, base_dir="midi"):
        super().__init__(base_dir, MidiFileNHotTimeSeries)
        self.n_features = 128 + len(DURATION_BINS) + 4





if __name__ == "__main__":

    # dataset = VectorGetterNHot("raw_midi")
    # X_train, X_test, y_train, y_test = dataset.get_all_split("train")

    dataset = VectorGetterNHot("midi/classical")
    # while dataset.last_train_chunk_i < dataset.n_train_files:
    #     X, y = dataset.get_chunk(BATCH_FILES, "train")
