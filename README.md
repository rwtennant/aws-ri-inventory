# AWS Reserved Instance Inventory Tool

A desktop application to understand your current inventory of AWS reserved instances and their status on the RI marketplace. The need for this tool arose when we had purchased a large number of RIs and started to sell them on the RI marketplace. The AWS console does not provide a single place to see all your RIs along with their status on the RI marketplace - you would have to go into the EC2 console and scroll through RIs one by one, noting their disposition as you go.

This application allows you see all your RIs, how much they've been utilized over the last 30 days and if they are currently listed on the RI marketplace or have been sold.

## Features

- 🔍 **Fetch RI Data**: Retrieve Reserved Instance inventory, listings, and utilization data
- 📊 **Interactive Table**: Sortable columns with search and filter capabilities  
- 📁 **Export Functionality**: Save results to CSV with clean formatting
- 🎨 **Modern UI**: Clean, professional interface built with tkinter
- 🔒 **Secure**: Uses temporary AWS credentials (no storage)

## Screenshots

![Main Interface](screenshots/main-window.png)
![Data View](screenshots/data-view.png)

## Requirements

- Python 3.7+
- AWS credentials with appropriate permissions

## Installation

### Option 1: Clone and Run
```bash
git clone https://github.com/yourusername/aws-ri-inventory.git
cd aws-ri-inventory
pip install -r requirements.txt
python aws_ri_inventory.py
```

### Option 2: Download Release
Download the latest release from the [Releases page](https://github.com/yourusername/aws-ri-inventory/releases).

## Usage

1. **Get AWS Credentials**: Obtain temporary AWS credentials from:
   - AWS CLI: `aws sts get-session-token`
   - AWS Console: Use temporary credentials from your session
   
2. **Launch Application**:
   ```bash
   python aws_ri_inventory.py
   ```

3. **Enter Credentials**: Input your AWS Access Key ID, Secret Access Key, and Session Token

4. **Fetch Data**: Click "Fetch Data" to retrieve your Reserved Instance information

5. **Analyze Results**: Use the interactive table to:
   - Sort by clicking column headers
   - Search across all fields
   - Filter by RI state
   - Export to CSV

## AWS Permissions Required

Your AWS credentials need the following permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeReservedInstances",
                "ec2:DescribeReservedInstancesListings",
                "ce:GetReservationUtilization"
            ],
            "Resource": "*"
        }
    ]
}
```

## Supported Regions

The tool checks these AWS regions by default:
- `ca-central-1` (Canada Central)
- `eu-west-1` (Europe West)
- `us-west-2` (US West)
- `ap-northeast-1` (Asia Pacific Northeast)

## Data Collected

- **Reserved Instances**: ID, start/end dates, state, region, instance type
- **RI Listings**: Marketplace listings, status, days on market
- **Utilization**: Usage percentages, unused hours, net savings

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/aws-ri-inventory/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/aws-ri-inventory/discussions)

## Changelog

### v1.0.0
- Initial release
- GUI interface for AWS RI data retrieval
- Interactive data table with sorting and filtering
- CSV export functionality
- Support for multiple AWS regions

---

**⚠️ Security Note**: This application uses temporary AWS credentials and does not store any sensitive information locally.