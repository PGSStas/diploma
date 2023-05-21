import typing as tp

from abc import ABC, abstractclassmethod

from news import Article

class Scraper(ABC):
    @abstractclassmethod
    def parse_pages(self) -> tp.List[Article]:
        pass

    @abstractclassmethod
    def validate_page(self) -> bool:
        pass

    @abstractclassmethod
    def find_all_urls(self) -> tp.List[str]:
        pass
