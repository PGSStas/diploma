from dataclasses import dataclass


@dataclass
class Article:
    """
        Some news article
    """
    title: str
    date: str
    author: str
    url: str
    text: str

    def __str__(self) -> str:
        msg = self.title + " by " + self.author + '\n'
        msg += f"  ---- {self.date} ----  \n\n"
        msg += self.text + '\n\n'
        msg += "  -------------------------------------  \n"
        msg += f"More: {self.url}\n"
        return msg

    def __repr__(self) -> str:
        return self.__str__()
