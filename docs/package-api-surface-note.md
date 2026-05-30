# Package API Surface Note

Meridian should expose stable, intentional package-root imports from `meridian_core.__init__`.

Do not automatically export every class from every module. Root exports should be reserved for:

- stable domain objects callers are expected to use directly
- primary builder/loader functions
- small enums that are part of public decision contracts

Prefer module-level imports for experimental or internal helpers.

## Current Export Direction

Already exported:

```python
from meridian_core import build_progress_intention
from meridian_core import ProgressIntention
from meridian_core import MissionObjectiveLine
from meridian_core import ObjectiveStage
```

Candidates for deliberate future export:

```python
load_mission
find_mission_file
build_wake_brief
get_mission_objectives
assess_tier
assess_blocked_action
route_from_tier
make_initial_registry
```

Review these as public API decisions before adding them.
