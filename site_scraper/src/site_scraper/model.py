import numpy as np
import typing as tp
import nltk
from nltk.tokenize import word_tokenize

from tqdm import tqdm


import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split

from sklearn.metrics import confusion_matrix
import seaborn as sns


UNKNOWN_TOKEN = 0
PADDING_TOKEN = 1
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

PAD_SIZE = 32


def tokenize_corpus(corpus: tp.List[tp.List[tp.Tuple[str, str]]]) -> tp.Mapping[str, int]:
    id = 2
    mapping: tp.Mapping[str, int] = {
        "####UNKNOWN_TOKEN": UNKNOWN_TOKEN, "###PADDING_TOKEN": PADDING_TOKEN}
    for part in corpus:
        for item, _ in part:
            for token in word_tokenize(item):
                if token not in mapping:
                    mapping[token] = id
                    id += 1
    return mapping


def words_to_ids(mapping: tp.Mapping[str, int], words: str) -> tp.List[int]:
    ans = []
    for token in word_tokenize(words):
        if token in mapping:
            ans.append(mapping[token])
        else:
            ans.append(UNKNOWN_TOKEN)
    while len(ans) < PAD_SIZE:
        ans.append(PADDING_TOKEN)
    return ans


class EmbedModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, class_count):
        super(EmbedModel, self).__init__()
        self.embeddings = nn.Embedding(
            vocab_size, embedding_dim, padding_idx=PADDING_TOKEN)
        self.lstm = nn.LSTM(32 * embedding_dim, hidden_dim, bidirectional=True)
        self.drop = nn.Dropout(p=0.25)
        self.linear1 = nn.Linear(hidden_dim * 2, class_count)
        # self.linear2 = nn.Linear(64, class_count)

    def forward(self, x):
        input_shape = x.shape
        # print(x.shape)
        x = self.embeddings(x)
        # print(x.shape)
        x, _ = self.lstm(x.view(input_shape[0], -1))
        # print(x.shape)
        x = self.drop(x)
        x = self.linear1(x)
        # x = F.relu(x)
        # x = self.linear2(x)
        return F.log_softmax(x, dim=1)


def test_model(model: nn.Module, test_data):
    loss_function = nn.NLLLoss()
    model.eval()
    accum_loss = 0
    for batch in test_data:
        X = batch['X'].to(DEVICE)
        y = batch['y'].to(DEVICE)
        tag_scores = model(X)

        loss = loss_function(tag_scores, y)
        accum_loss += loss
    return float(loss)


def train_model(model: nn.Module, training_data, test_data):
    loss_function = nn.NLLLoss()
    optimizer = optim.SGD(model.parameters(), lr=0.1)
    for epoch in range(1000):
        accum_loss = 0
        model.train()
        for batch in training_data:
            X = batch['X'].to(DEVICE)
            y = batch['y'].to(DEVICE)
            model.zero_grad()

            tag_scores = model(X)

            loss = loss_function(tag_scores, y)
            accum_loss += loss
            loss.backward()
            optimizer.step()
        print(
            f'------------------ EPOCH {epoch + 1} -----------------------')
        print("  LOSS:", accum_loss)
        if (epoch + 1) % 5 == 0:
            test_loss = test_model(model, test_data)
            print("  TEST LOSS:", test_loss)

            torch.save(model.state_dict(), f"model_{float(test_loss):.5}.pt")


class SentenceDataset(Dataset):
    def __init__(self, X, y):
        self.X = X
        self.y = y

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        return {'X': torch.tensor(self.X[idx], device=DEVICE), 'y': self.y[idx]}


def main():
    nltk.download('punkt')
    with open("filter_categories_1k.txt", 'rb') as f:
        inp = np.load(f, allow_pickle=True)
    mapping = tokenize_corpus(inp)
    print(len(mapping))

    class_count = len(inp)
    X, y = [], []
    for i, cur_class in enumerate(inp):
        for t, _ in cur_class:
            X.append(words_to_ids(mapping, t))
            y.append(i)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42)
    model = EmbedModel(len(mapping), 100, 128, class_count).to(DEVICE)
    model.load_state_dict(torch.load('model_0.40832.pt'))
    train_dataset = SentenceDataset(X_train, y_train)
    train_dataloader = DataLoader(train_dataset, batch_size=200, shuffle=True)
    test_dataset = SentenceDataset(X_test, y_test)
    test_dataloader = DataLoader(test_dataset, batch_size=200, shuffle=False)
    # print(y_test)
    # train_model(model, train_dataloader, test_dataloader)
    pred = torch.argmax(model(test_dataset[:]['X']), dim=1) 
    # print(y_test)
    values = torch.tensor(test_dataset[:]['y'])
    print(torch.sum(pred == values) / len(values))

    conf = confusion_matrix(values, pred)
    

if __name__ == "__main__":
    main()
