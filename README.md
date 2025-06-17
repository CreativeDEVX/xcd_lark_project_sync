# Lark Project Sync for Odoo 18

This module integrates Odoo Projects with Lark Tasks, enabling seamless task synchronization between the two platforms.

## Features

- **Bidirectional Sync**: Keep tasks in sync between Odoo and Lark
- **Project Integration**: Link Odoo projects with Lark task lists
- **Task Management**: Create, update, and track tasks from within Odoo
- **Automatic Synchronization**: Scheduled sync to keep data consistent
- **User Assignment**: Assign tasks to Odoo users
- **Status Tracking**: Track task status with custom workflows
- **Due Date Management**: Set and monitor task deadlines
- **Rich Text Descriptions**: Support for rich text in task descriptions
- **Activity Logs**: Track changes and updates to tasks
- **Email Notifications**: Get notified about task assignments and updates

## Installation

1. Install the module:
   ```bash
   python3 odoo-bin -i xcd_lark_project_sync --stop-after-init
   ```

2. Configure Lark API credentials in Odoo Settings:
   - Go to Settings > General Settings > Lark Integration
   - Enter your Lark App ID and App Secret
   - Configure the default project and task settings

3. Restart your Odoo server

## Configuration

### Lark API Setup
1. Create a new application in the [Lark Developer Console](https://open.larksuite.com/)
2. Enable the following permissions:
   - Task: Read/Write access
   - User: Read access
3. Set the redirect URI to: `https://your-odoo-instance.com/lark/oauth/callback`
4. Copy the App ID and App Secret to Odoo settings

### Odoo Settings
Navigate to Settings > General Settings > Lark Integration and configure:
- Enable/Disable the integration
- Set default project for new tasks
- Configure sync frequency
- Set up email notifications

## Usage

### Syncing Projects with Lark
1. Go to Project > Configuration > Projects
2. Open a project
3. Click on the "Link with Lark" button
4. Select a Lark task list to sync with
5. Click "Link" to establish the connection

### Managing Tasks
- **Create Tasks**: Create tasks in either Odoo or Lark
- **Update Tasks**: Changes made in either system will sync automatically
- **Task Status**: Update task status in either system
- **Assignments**: Assign tasks to team members
- **Due Dates**: Set and track task deadlines

### Manual Sync
To manually sync tasks:
1. Go to Project > Configuration > Projects
2. Open a linked project
3. Click the "Sync with Lark" button

## Technical Information

### Dependencies
- Odoo 18.0+
- Python packages:
  - lark-oapi
  - requests

### Data Model
- `lark.task`: Stores Lark task data
- `lark.tasklist`: Represents Lark task lists
- `project.project`: Extended with Lark integration fields
- `project.task`: Extended with Lark task reference

### API Integration
- OAuth 2.0 for authentication
- REST API for data synchronization
- Webhooks for real-time updates

## Troubleshooting

### Common Issues
1. **Sync Not Working**
   - Check API credentials
   - Verify network connectivity
   - Check Odoo logs for errors

2. **Authentication Errors**
   - Ensure correct App ID and Secret
   - Check token expiration
   - Re-authenticate if needed

3. **Missing Permissions**
   - Verify Lark app permissions
   - Check user access rights in Odoo

## Support

For support, please contact:
- Email: support@creativedev.co.th
- Website: https://www.creativedev.co.th/support

## License

This module is licensed under LGPL-3.

---
*Developed by Your Creative Dev Co.,Ltd.*
