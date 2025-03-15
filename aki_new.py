"""
A simplified and improved Akinator API client
"""
import httpx
from bs4 import BeautifulSoup

class AkinatorError(Exception):
    pass

class CantGoBackAnyFurther(AkinatorError):
    pass

class InvalidLanguageError(AkinatorError):
    pass

LANG_MAP = {
    "english": "en", "arabic": "ar", "chinese": "cn", "german": "de",
    "spanish": "es", "french": "fr", "hebrew": "il", "italian": "it",
    "japanese": "jp", "korean": "kr", "dutch": "nl", "polish": "pl",
    "portuguese": "pt", "russian": "ru", "turkish": "tr", "indonesian": "id"
}

THEME_MAP = {
    "characters": 1, "objects": 2, "animals": 14,
    "c": 1, "o": 2, "a": 14
}

THEMES = {
    "en": ["characters", "animals", "objects"],
    "ar": ["characters"],
    "cn": ["characters"],
    "de": ["characters", "animals"],
    "es": ["characters", "animals"],
    "fr": ["characters", "animals", "objects"],
    "il": ["characters"],
    "it": ["characters", "animals"],
    "jp": ["characters", "animals"],
    "kr": ["characters"],
    "nl": ["characters"],
    "pl": ["characters"],
    "pt": ["characters"],
    "ru": ["characters"],
    "tr": ["characters"],
    "id": ["characters"],
}

ANSWERS = {
    "yes": 0, "y": 0, "0": 0,
    "no": 1, "n": 1, "1": 1,
    "idk": 2, "i": 2, "i dont know": 2, "i don't know": 2, "2": 2,
    "probably": 3, "p": 3, "3": 3,
    "probably not": 4, "pn": 4, "4": 4
}

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

class Akinator:
    """
    The Akinator API client class for interacting with the Akinator game.
    """

    def __init__(self):
        # Base attributes
        self.uri = None
        self.lang = None
        self.theme = None
        self.child_mode = False
        self.available_themes = None

        # Game state
        self.session = None
        self.signature = None
        self.question = None
        self.progression = 0.0
        self.step = 0
        self.step_last_proposition = 0
        self.akitude = None

        # Result attributes
        self.win = False
        self.name_proposition = None
        self.description_proposition = None
        self.photo = None
        self.pseudo = None
        self.completion = None

    async def _request(self, url, method="GET", data=None):
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=HEADERS, timeout=30.0)
                else:  # POST
                    response = await client.post(url, headers=HEADERS, json=data, timeout=30.0)

                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as e:
            raise AkinatorError(f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise AkinatorError(f"Request error: {str(e)}")
        except Exception as e:
            raise AkinatorError(f"Request failed: {str(e)}")

    async def _update_from_answer(self, response_data):
        if "id_proposition" in response_data:
            # We have a guess
            self.win = True
            self.name_proposition = response_data.get("name_proposition")
            self.description_proposition = response_data.get("description_proposition")
            self.photo = response_data.get("photo")
            self.pseudo = response_data.get("pseudo", "")
            self.step_last_proposition = self.step
        else:
            # Continue with questions
            self.win = False
            self.akitude = response_data.get("akitude")
            self.step = int(response_data.get("step", 0))
            self.progression = float(response_data.get("progression", 0.0))
            self.question = response_data.get("question")

        self.completion = response_data.get("completion")

    async def start_game(self, language="en", theme="characters", child_mode=False):
        """
        Start a new Akinator game session.

        Args:
            language (str): Language code or name (default: "en")
            theme (str): Game theme - "characters", "animals", or "objects" (default: "characters")
            child_mode (bool): Enable child mode (default: False)

        Returns:
            str: The first question
        """
        if language in LANG_MAP:
            language = LANG_MAP[language]
        elif language not in LANG_MAP.values():
            raise InvalidLanguageError(f"Language '{language}' is not supported")

        self.lang = language
        self.uri = f"https://{language}.akinator.com"
        self.child_mode = child_mode
        self.available_themes = THEMES.get(language, ["characters"])

        if theme not in THEME_MAP and theme not in self.available_themes:
            theme = self.available_themes[0]
        self.theme = THEME_MAP.get(theme, 1)

        url = f"{self.uri}/game"
        data = {"sid": self.theme, "cm": str(child_mode).lower()}
        response = await self._request(url, "POST", data)
        soup = BeautifulSoup(response.text, "html.parser")
        ask_soundlike = soup.find(id="askSoundlike")
        if ask_soundlike:
            self.session = ask_soundlike.find(id="session").get("value")
            self.signature = ask_soundlike.find(id="signature").get("value")
        else:
            raise AkinatorError("Failed to extract session information")

        question_label = soup.find(id="question-label")
        if question_label:
            self.question = question_label.get_text()
        else:
            raise AkinatorError("Failed to extract question")
        self.progression = 0.0
        self.step = 0
        self.win = False
        
        return self.question

    async def answer(self, answer):
        """
        Submit an answer to the current question.

        Args:
            answer (str): One of "yes"/"y", "no"/"n", "idk", "probably"/"p", or "probably not"/"pn"

        Returns:
            bool: True if Akinator has a guess, False if more questions
        """
        answer_id = ANSWERS.get(answer.lower(), -1)
        if answer_id == -1:
            raise AkinatorError(f"Invalid answer '{answer}'. Use yes/y, no/n, idk, probably/p, or probably not/pn")

        data = {
            "step": self.step,
            "progression": self.progression,
            "sid": self.theme,
            "cm": str(self.child_mode).lower(),
            "answer": answer_id,
            "session": self.session,
            "signature": self.signature,
        }

        if self.step_last_proposition:
            data["step_last_proposition"] = self.step_last_proposition

        url = f"{self.uri}/answer"
        response = await self._request(url, "POST", data)
        response_data = response.json()
        await self._update_from_answer(response_data)
        
        return self.win

    async def back(self):
        """
        Go back to the previous question.

        Returns:
            str: The previous question
        """
        if self.step == 0:
            raise CantGoBackAnyFurther("Cannot go back from the first question")

        data = {
            "step": self.step,
            "progression": self.progression,
            "sid": self.theme,
            "cm": str(self.child_mode).lower(),
            "session": self.session,
            "signature": self.signature,
        }

        url = f"{self.uri}/cancel_answer"
        response = await self._request(url, "POST", data)
        response_data = response.json()

        # Update state
        self.akitude = response_data.get("akitude")
        self.step = int(response_data.get("step", 0))
        self.progression = float(response_data.get("progression", 0.0))
        self.question = response_data.get("question")
        self.win = False

        return self.question

    async def exclude(self):
        """
        Exclude the current guess and continue with more questions.

        Returns:
            str: The next question
        """
        if not self.win:
            raise AkinatorError("Cannot exclude when there is no guess")

        data = {
            "step": self.step,
            "progression": self.progression,
            "sid": self.theme,
            "cm": str(self.child_mode).lower(),
            "session": self.session,
            "signature": self.signature,
            "step_last_proposition": self.step
        }

        url = f"{self.uri}/exclude"
        response = await self._request(url, "POST", data)
        response_data = response.json()

        # Reset win state
        self.win = False
        self.name_proposition = None
        self.description_proposition = None
        self.photo = None

        # Update state
        self.akitude = response_data.get("akitude")
        self.step = int(response_data.get("step", 0))
        self.progression = float(response_data.get("progression", 0.0))
        self.question = response_data.get("question")
        
        return self.question

    def get_guess(self):
        """
        Get the current guess information.

        Returns:
            dict: Guess information including name, description, and photo
        """
        if not self.win:
            return None

        return {
            "name": self.name_proposition,
            "description": self.description_proposition,
            "photo": self.photo
        }

# Example usage
# async def play_akinator():
#     aki = Akinator()
#     question = await aki.start_game(language="en", theme="characters")
#     print(f"First question: {question}")

#     # Answer loop
#     while True:
#         # Get user answer
#         print("\nYour answer (y/n/idk/p/pn/b to go back): ", end="")
#         answer = input().strip().lower()

#         if answer == "b":
#             try:
#                 question = await aki.back()
#                 print(f"Previous question: {question}")
#             except CantGoBackAnyFurther:
#                 print("Cannot go back any further!")
#         else:
#             try:
#                 is_guess = await aki.answer(answer)

#                 if is_guess:
#                     # We have a guess
#                     guess = aki.get_guess()
#                     print(f"\nI think of: {guess['name']}")
#                     print(f"Description: {guess['description']}")

#                     print("\nAm I correct? (y/n): ", end="")
#                     is_correct = input().strip().lower()

#                     if is_correct in ["y", "yes"]:
#                         print("Great! I guessed correctly!")
#                         break
#                     else:
#                         # Exclude and continue
#                         question = await aki.exclude()
#                         print(f"Let me try again. {question}")
#                 else:
#                     # Continue with next question
#                     print(f"Question {aki.step+1} ({aki.progression}%): {aki.question}")
#             except AkinatorError as e:
#                 print(f"Error: {e}")

# import asyncio
# asyncio.run(play_akinator())