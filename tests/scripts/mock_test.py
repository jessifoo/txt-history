from unittest.mock import Mock
from dataclasses import dataclass

# Create a simple class to mock
@dataclass
class Args:
    name: str
    output: str | None = None

# The way we had it before
mock1 = Mock(name="Phil")
print(f"Without spec: type={type(mock1.name)}, value={mock1.name}")

# The corrected way
mock2 = Mock(spec=Args)
mock2.name = "Phil"
print(f"With spec: type={type(mock2.name)}, value={mock2.name}")

# Another way using autospec
mock3 = Mock(autospec=Args)
mock3.name = "Phil"
print(f"With autospec: type={type(mock3.name)}, value={mock3.name}")
