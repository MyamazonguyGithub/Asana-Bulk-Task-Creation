# Bulk Asana Task Creation

## Overview

This script automates the process of creating tasks across boards in Asana. It interacts with HubSpot & Asana APIs to fetch information and create tasks.

## Features

- Automates the creation of tasks.
- Handles errors during the duplication process.
- Skips task creation if task already exists
- Produces list of skipped/errored/created tasks
- Allows toggle between HubSpot generated project GID list and manual entry GID list

## Installation

1. Clone the repository.
2. Ensure Python 3.x is installed.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Set use_gid_list to True

  ```bash
  use_gid_list = True
   ```

2. Input single GID in GID List to test

  ```bash
  process_gids = ['0000000000000000'] 
   ```
3. Run the script to test task creation on single GID:

```bash
python asana-task-creation.py
```

4. Review Asana task created for errors
5. Once test task is approved, set use_gid_list to False

  ```bash
  use_gid_list = False
   ```

6. Review terminal output for errors.

  ```bash
   Created Total: XX | GIDs: set('0000000000000000','0000000000000000','0000000000000000')
   Errored Total: XX | GIDs: set('0000000000000000','0000000000000000','0000000000000000')
   Skipped Total: XX
   Combined Total: XXX
   ```
 
7. Use Error GID List to input new GID List, set use_gid_list to True and troubleshoot HubSpot data errors

 ```bash
  use_gid_list = True
   ```
  ```bash
    process_gids = ['0000000000000000','0000000000000000','0000000000000000']
   ```

8. Once errored GIDs have processed succsefully, set use_gid_list to False and run again

  ```bash
  use_gid_list = False
   ```
9. Output should state all skipped due to existing task. This means all tasks have been created and task creation is complete.

  ```bash
   Created Total: 0 | GIDs: set()
   Errored Total: 0 | GIDs: set()
   Skipped Total: XXX
   Combined Total: XXX
   ```

## Contribution

This is a private repository. To implement changes:

1. **Create a Branch**: Before making your changes, create a new branch from the main branch. Name it appropriately related to the feature or fix you're working on:

    ```bash
    git checkout -b feature/<your-feature-name>
    ```

2. **Make Changes**: Implement your changes or additions in your branch.

3. **Test Your Changes**: Ensure that your changes do not break existing functionality.

4. **Commit Changes**: Add and commit your changes. Make sure your commit messages are clear:

    ```bash
    git add .
    git commit -m "Add a detailed commit message describing the change"
    ```

5. **Push Changes**: Push your branch to the repository:

    ```bash
    git push origin feature/<your-feature-name>
    ```

6. **Open a Pull Request (PR)**: Go to the repository on GitHub, you'll see a 'Compare & pull request' button for your branch. Click it, review the changes, and then create the pull request.

7. **Code Review**: Wait for the internal review process. Make any required updates. The repository manager will merge it once it is approved.

## License

This project is proprietary. Unauthorized copying, modification, distribution, or use is not allowed.
