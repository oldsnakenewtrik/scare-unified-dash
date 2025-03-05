const Imap = require('imap');
const { simpleParser } = require('mailparser');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { Client } = require('pg');
const cron = require('node-cron');
const winston = require('winston');
require('dotenv').config();

// Initialize logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ level, message, timestamp }) => {
      return `${timestamp} ${level}: ${message}`;
    })
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'salesforce_connector.log' })
  ]
});

// Configuration from environment variables
const config = {
  imap: {
    user: process.env.EMAIL_USER,
    password: process.env.EMAIL_PASSWORD,
    host: process.env.EMAIL_HOST || 'imap.gmail.com',
    port: parseInt(process.env.EMAIL_PORT) || 993,
    tls: process.env.EMAIL_TLS !== 'false',
    tlsOptions: { rejectUnauthorized: process.env.EMAIL_REJECT_UNAUTHORIZED !== 'false' }
  },
  email: {
    fromAddress: process.env.EMAIL_FROM_ADDRESS || '',
    subject: process.env.EMAIL_SUBJECT_FILTER || 'Salesforce Daily Report',
    markSeen: process.env.MARK_EMAILS_AS_SEEN !== 'false'
  },
  cron: {
    schedule: process.env.CRON_SCHEDULE || '0 */12 * * *' // Every 12 hours by default
  },
  database: {
    connectionString: process.env.DATABASE_URL || 'postgresql://scare_user:scare_password@postgres:5432/scare_metrics',
    schema: process.env.DB_SCHEMA || 'scare_metrics'
  },
  tempDir: process.env.TEMP_DIR || './temp'
};

// Ensure temp directory exists
if (!fs.existsSync(config.tempDir)) {
  fs.mkdirSync(config.tempDir, { recursive: true });
}

// Database connection
const dbClient = new Client({
  connectionString: config.database.connectionString
});

// Function to connect to the database
async function connectToDatabase() {
  try {
    await dbClient.connect();
    logger.info('Connected to database');
    return true;
  } catch (error) {
    logger.error(`Database connection error: ${error.message}`);
    return false;
  }
}

// Function to get date dimension ID
async function getDateDimensionId(date) {
  try {
    // Check if date exists
    const checkQuery = {
      text: `SELECT date_id FROM ${config.database.schema}.dim_date WHERE full_date = $1`,
      values: [date]
    };
    
    const checkResult = await dbClient.query(checkQuery);
    
    if (checkResult.rows.length > 0) {
      return checkResult.rows[0].date_id;
    }
    
    // Date doesn't exist, create it
    const dateObj = new Date(date);
    const dayOfWeek = dateObj.getDay();
    const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
    const month = dateObj.getMonth() + 1;
    const monthName = dateObj.toLocaleDateString('en-US', { month: 'long' });
    const quarter = Math.floor((dateObj.getMonth() / 3)) + 1;
    const year = dateObj.getFullYear();
    const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);
    
    const insertQuery = {
      text: `
        INSERT INTO ${config.database.schema}.dim_date 
        (full_date, day_of_week, day_name, month, month_name, quarter, year, is_weekend)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING date_id
      `,
      values: [date, dayOfWeek, dayName, month, monthName, quarter, year, isWeekend]
    };
    
    const insertResult = await dbClient.query(insertQuery);
    return insertResult.rows[0].date_id;
  } catch (error) {
    logger.error(`Error getting date dimension ID: ${error.message}`);
    throw error;
  }
}

// Function to get campaign dimension ID
async function getCampaignDimensionId(campaignName) {
  try {
    // Check if campaign exists
    const checkQuery = {
      text: `
        SELECT campaign_id 
        FROM ${config.database.schema}.dim_campaign 
        WHERE campaign_name = $1 AND source_system = 'Salesforce'
      `,
      values: [campaignName]
    };
    
    const checkResult = await dbClient.query(checkQuery);
    
    if (checkResult.rows.length > 0) {
      return checkResult.rows[0].campaign_id;
    }
    
    // Campaign doesn't exist, create it
    const today = new Date().toISOString().split('T')[0];
    
    const insertQuery = {
      text: `
        INSERT INTO ${config.database.schema}.dim_campaign 
        (campaign_name, source_system, created_date, updated_date, is_active)
        VALUES ($1, 'Salesforce', $2, $2, TRUE)
        RETURNING campaign_id
      `,
      values: [campaignName, today]
    };
    
    const insertResult = await dbClient.query(insertQuery);
    return insertResult.rows[0].campaign_id;
  } catch (error) {
    logger.error(`Error getting campaign dimension ID: ${error.message}`);
    throw error;
  }
}

// Function to process CSV file and store data in database
async function processCSVFile(filePath) {
  return new Promise((resolve, reject) => {
    const results = [];
    
    fs.createReadStream(filePath)
      .pipe(csv())
      .on('data', (data) => results.push(data))
      .on('end', async () => {
        try {
          logger.info(`Processing CSV file with ${results.length} records`);
          
          for (const row of results) {
            // Extract date from CSV
            // Assuming the CSV has a date column like 'Date' or 'Report_Date'
            let recordDate = row.Date || row.Report_Date;
            if (!recordDate) {
              // If date not found in CSV, use yesterday's date
              const yesterday = new Date();
              yesterday.setDate(yesterday.getDate() - 1);
              recordDate = yesterday.toISOString().split('T')[0];
            }
            
            // Extract campaign from CSV
            // Assuming the CSV has a campaign column like 'Campaign_Name' or 'Campaign'
            const campaignName = row.Campaign_Name || row.Campaign || 'Unknown Campaign';
            
            // Get dimension IDs
            const dateId = await getDateDimensionId(recordDate);
            const campaignId = await getCampaignDimensionId(campaignName);
            
            // Prepare data
            const leads = parseInt(row.Leads || row.Total_Leads || 0, 10);
            const qualifiedLeads = parseInt(row.Qualified_Leads || row.MQLs || 0, 10);
            const opportunities = parseInt(row.Opportunities || 0, 10);
            const closedWon = parseInt(row.Closed_Won || row.Won_Deals || 0, 10);
            const closedLost = parseInt(row.Closed_Lost || row.Lost_Deals || 0, 10);
            const revenue = parseFloat(row.Revenue || row.Total_Revenue || 0);
            
            // Check if record already exists
            const checkQuery = {
              text: `
                SELECT salesforce_id 
                FROM ${config.database.schema}.fact_salesforce 
                WHERE date_id = $1 AND campaign_id = $2
              `,
              values: [dateId, campaignId]
            };
            
            const existingRecord = await dbClient.query(checkQuery);
            
            if (existingRecord.rows.length > 0) {
              // Update existing record
              const updateQuery = {
                text: `
                  UPDATE ${config.database.schema}.fact_salesforce
                  SET 
                    leads = $3,
                    qualified_leads = $4,
                    opportunities = $5,
                    closed_won = $6,
                    closed_lost = $7,
                    revenue = $8,
                    source_data = $9,
                    updated_at = NOW()
                  WHERE date_id = $1 AND campaign_id = $2
                `,
                values: [
                  dateId, 
                  campaignId, 
                  leads, 
                  qualifiedLeads, 
                  opportunities, 
                  closedWon, 
                  closedLost, 
                  revenue, 
                  JSON.stringify(row)
                ]
              };
              
              await dbClient.query(updateQuery);
            } else {
              // Insert new record
              const insertQuery = {
                text: `
                  INSERT INTO ${config.database.schema}.fact_salesforce
                  (date_id, campaign_id, leads, qualified_leads, opportunities, closed_won, closed_lost, revenue, source_data, created_at, updated_at)
                  VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
                `,
                values: [
                  dateId, 
                  campaignId, 
                  leads, 
                  qualifiedLeads, 
                  opportunities, 
                  closedWon, 
                  closedLost, 
                  revenue, 
                  JSON.stringify(row)
                ]
              };
              
              await dbClient.query(insertQuery);
            }
          }
          
          logger.info('Successfully processed and stored CSV data');
          resolve();
        } catch (error) {
          logger.error(`Error processing CSV file: ${error.message}`);
          reject(error);
        }
      })
      .on('error', (error) => {
        logger.error(`Error reading CSV file: ${error.message}`);
        reject(error);
      });
  });
}

// Function to check emails and download CSV attachments
function checkEmails() {
  return new Promise((resolve, reject) => {
    try {
      const imap = new Imap(config.imap);
      
      imap.once('ready', () => {
        imap.openBox('INBOX', false, (err, box) => {
          if (err) {
            logger.error(`Error opening inbox: ${err.message}`);
            imap.end();
            return reject(err);
          }
          
          // Create search criteria
          const searchCriteria = ['UNSEEN'];
          
          if (config.email.fromAddress) {
            searchCriteria.push(['FROM', config.email.fromAddress]);
          }
          
          if (config.email.subject) {
            searchCriteria.push(['SUBJECT', config.email.subject]);
          }
          
          imap.search(searchCriteria, (err, results) => {
            if (err) {
              logger.error(`Error searching emails: ${err.message}`);
              imap.end();
              return reject(err);
            }
            
            if (!results || results.length === 0) {
              logger.info('No matching emails found');
              imap.end();
              return resolve([]);
            }
            
            logger.info(`Found ${results.length} matching emails`);
            
            const f = imap.fetch(results, {
              bodies: '',
              markSeen: config.email.markSeen
            });
            
            const promises = [];
            
            f.on('message', (msg, seqno) => {
              logger.info(`Processing email #${seqno}`);
              
              const promise = new Promise((resolveMessage, rejectMessage) => {
                msg.on('body', (stream, info) => {
                  simpleParser(stream, async (err, parsed) => {
                    if (err) {
                      logger.error(`Error parsing email: ${err.message}`);
                      return rejectMessage(err);
                    }
                    
                    logger.info(`Email subject: ${parsed.subject}`);
                    
                    if (!parsed.attachments || parsed.attachments.length === 0) {
                      logger.info('No attachments found in email');
                      return resolveMessage(null);
                    }
                    
                    const csvAttachments = parsed.attachments.filter(att => 
                      att.filename && att.filename.toLowerCase().endsWith('.csv')
                    );
                    
                    if (csvAttachments.length === 0) {
                      logger.info('No CSV attachments found in email');
                      return resolveMessage(null);
                    }
                    
                    logger.info(`Found ${csvAttachments.length} CSV attachments`);
                    
                    try {
                      for (const attachment of csvAttachments) {
                        const filePath = path.join(config.tempDir, attachment.filename);
                        
                        // Save attachment to file
                        fs.writeFileSync(filePath, attachment.content);
                        logger.info(`Saved attachment to ${filePath}`);
                        
                        // Process the CSV file
                        await processCSVFile(filePath);
                        
                        // Delete the temporary file
                        fs.unlinkSync(filePath);
                        logger.info(`Deleted temporary file ${filePath}`);
                      }
                      
                      resolveMessage(true);
                    } catch (error) {
                      logger.error(`Error processing attachments: ${error.message}`);
                      rejectMessage(error);
                    }
                  });
                });
              });
              
              promises.push(promise);
            });
            
            f.once('error', (err) => {
              logger.error(`Fetch error: ${err.message}`);
              reject(err);
            });
            
            f.once('end', () => {
              logger.info('Finished fetching all messages');
              Promise.all(promises)
                .then(() => {
                  imap.end();
                  resolve(true);
                })
                .catch((err) => {
                  imap.end();
                  reject(err);
                });
            });
          });
        });
      });
      
      imap.once('error', (err) => {
        logger.error(`IMAP connection error: ${err.message}`);
        reject(err);
      });
      
      imap.once('end', () => {
        logger.info('IMAP connection ended');
      });
      
      imap.connect();
    } catch (error) {
      logger.error(`Error in checkEmails: ${error.message}`);
      reject(error);
    }
  });
}

// Main function to run the email checker
async function runEmailChecker() {
  try {
    logger.info('Starting email checking process');
    
    const dbConnected = await connectToDatabase();
    if (!dbConnected) {
      logger.error('Cannot proceed without database connection');
      return;
    }
    
    await checkEmails();
    logger.info('Email checking process completed');
  } catch (error) {
    logger.error(`Error in runEmailChecker: ${error.message}`);
  }
}

// Start the application
(async () => {
  try {
    logger.info('Starting Salesforce CSV email connector service');
    
    // Run immediately at startup
    await runEmailChecker();
    
    // Schedule to run at regular intervals
    cron.schedule(config.cron.schedule, async () => {
      logger.info(`Running scheduled email check (${config.cron.schedule})`);
      await runEmailChecker();
    });
    
    logger.info(`Service scheduled to run with cron pattern: ${config.cron.schedule}`);
  } catch (error) {
    logger.error(`Startup error: ${error.message}`);
    process.exit(1);
  }
})();
