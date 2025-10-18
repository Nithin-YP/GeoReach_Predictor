import csv
import random
import os

# Define states and districts
states = ['Andaman and Nicobar', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chandigarh', 'Chhattisgarh', 'Dadra and Nagar Haveli', 'Daman and Diu', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jammu and Kashmir', 'Jharkhand', 'Karnataka', 'Kerala', 'Lakshadweep', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'NCT of Delhi', 'Odisha', 'Puducherry', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal']

# Sample districts per state (simplified, not all)
districts_per_state = {
    'Andaman and Nicobar': ['Nicobar Islands', 'North and Middle Andaman', 'South Andaman'],
    'Andhra Pradesh': ['Anantapur', 'Chittoor', 'East Godavari', 'Guntur', 'Krishna', 'Kurnool', 'Nellore', 'Prakasam', 'Srikakulam', 'Visakhapatnam', 'Vizianagaram', 'West Godavari', 'Y.S.R.'],
    'Arunachal Pradesh': ['Anjaw', 'Changlang', 'Dibang Valley', 'East Kameng', 'East Siang', 'Kurung Kumey', 'Lohit', 'Longding', 'Lower Dibang Valley', 'Lower Subansiri', 'Namsai', 'Papum Pare', 'Tawang', 'Tirap', 'Upper Siang', 'Upper Subansiri', 'West Kameng', 'West Siang'],
    'Assam': ['Baksa', 'Barpeta', 'Bongaigaon', 'Cachar', 'Chirang', 'Darrang', 'Dhemaji', 'Dhubri', 'Dibrugarh', 'Dima Hasao', 'Goalpara', 'Golaghat', 'Hailakandi', 'Jorhat', 'Kamrup', 'Kamrup Metropolitan', 'Karbi Anglong', 'Karimganj', 'Kokrajhar', 'Lakhimpur', 'Morigaon', 'Nagaon', 'Nalbari', 'Sivasagar', 'Sonitpur', 'Tinsukia', 'Udalguri'],
    'Bihar': ['Araria', 'Arwal', 'Aurangabad', 'Banka', 'Begusarai', 'Bhagalpur', 'Bhojpur', 'Buxar', 'Darbhanga', 'Gaya', 'Gopalganj', 'Jamui', 'Jehanabad', 'Kaimur', 'Katihar', 'Khagaria', 'Kishanganj', 'Lakhisarai', 'Madhepura', 'Madhubani', 'Munger', 'Muzaffarpur', 'Nalanda', 'Nawada', 'Pashchim Champaran', 'Patna', 'Purba Champaran', 'Purnia', 'Rohtas', 'Saharsa', 'Samastipur', 'Saran', 'Sheikhpura', 'Sheohar', 'Sitamarhi', 'Siwan', 'Supaul', 'Vaishali'],
    'Chandigarh': ['Chandigarh'],
    'Chhattisgarh': ['Balod', 'Baloda Bazar', 'Balrampur', 'Bastar', 'Bemetara', 'Bijapur', 'Bilaspur', 'Dantewada', 'Dhamtari', 'Durg', 'Gariaband', 'Janjgir-Champa', 'Jashpur', 'Kabeerdham', 'Kondagaon', 'Korba', 'Koriya', 'Mahasamund', 'Mungeli', 'Narayanpur', 'Raigarh', 'Raipur', 'Rajnandgaon', 'Sukma', 'Surajpur', 'Surguja', 'Uttar Bastar Kanker'],
    'Dadra and Nagar Haveli': ['Dadra and Nagar Haveli'],
    'Daman and Diu': ['Daman', 'Diu'],
    'Goa': ['North Goa', 'South Goa'],
    'Gujarat': ['Ahmadabad', 'Amreli', 'Anand', 'Aravalli', 'Banas Kantha', 'Bharuch', 'Bhavnagar', 'Botad', 'Chhota Udaipur', 'Dahod', 'Devbhumi Dwarka', 'Gandhinagar', 'Gir Somnath', 'Jamnagar', 'Junagadh', 'Kachchh', 'Kheda', 'Mahesana', 'Mahisagar', 'Morbi', 'Narmada', 'Navsari', 'Panch Mahals', 'Patan', 'Porbandar', 'Rajkot', 'Sabar Kantha', 'Surat', 'Surendranagar', 'Tapi', 'The Dangs', 'Vadodara', 'Valsad'],
    'Haryana': ['Ambala', 'Bhiwani', 'Faridabad', 'Fatehabad', 'Gurgaon', 'Hisar', 'Jhajjar', 'Jind', 'Kaithal', 'Karnal', 'Kurukshetra', 'Mahendragarh', 'Mewat', 'Palwal', 'Panchkula', 'Panipat', 'Rewari', 'Rohtak', 'Sirsa', 'Sonipat', 'Yamunanagar'],
    'Himachal Pradesh': ['Bilaspur', 'Chamba', 'Hamirpur', 'Kangra', 'Kinnaur', 'Kullu', 'Lahul & Spiti', 'Mandi', 'Shimla', 'Sirmaur', 'Solan', 'Una'],
    'Jammu and Kashmir': ['Anantnag', 'Badgam', 'Bandipore', 'Baramulla', 'Doda', 'Ganderbal', 'Jammu', 'Kargil', 'Kathua', 'Kishtwar', 'Kulgam', 'Kupwara', 'Leh (Ladakh)', 'Poonch', 'Pulwama', 'Rajouri', 'Ramban', 'Reasi', 'Samba', 'Shupiyan', 'Srinagar', 'Udhampur'],
    'Jharkhand': ['Bokaro', 'Chatra', 'Deoghar', 'Dhanbad', 'Dumka', 'Garhwa', 'Giridih', 'Godda', 'Gumla', 'Hazaribagh', 'Jamtara', 'Khunti', 'Kodarma', 'Latehar', 'Lohardaga', 'Pakur', 'Palamu', 'Pashchimi Singhbhum', 'Purbi Singhbhum', 'Ramgarh', 'Ranchi', 'Sahibganj', 'Saraikela-kharsawan', 'Simdega'],
    'Karnataka': ['Bagalkot', 'Bangalore', 'Bangalore Rural', 'Belgaum', 'Bellary', 'Bidar', 'Bijapur', 'Chamrajnagar', 'Chikballapura', 'Chikmagalur', 'Chitradurga', 'Dakshina Kannada', 'Davanagere', 'Dharwad', 'Gadag', 'Gulbarga', 'Hassan', 'Haveri', 'Kodagu', 'Kolar', 'Koppal', 'Mandya', 'Mysore', 'Raichur', 'Ramanagara', 'Shimoga', 'Tumkur', 'Udupi', 'Uttara Kannada', 'Yadgir'],
    'Kerala': ['Alappuzha', 'Ernakulam', 'Idukki', 'Kannur', 'Kasaragod', 'Kollam', 'Kottayam', 'Kozhikode', 'Malappuram', 'Palakkad', 'Pathanamthitta', 'Thiruvananthapuram', 'Thrissur', 'Wayanad'],
    'Lakshadweep': ['Lakshadweep'],
    'Madhya Pradesh': ['Agar Malwa', 'Alirajpur', 'Anuppur', 'Ashoknagar', 'Balaghat', 'Barwani', 'Betul', 'Bhind', 'Bhopal', 'Burhanpur', 'Chhatarpur', 'Chhindwara', 'Damoh', 'Datia', 'Dewas', 'Dhar', 'Dindori', 'East Nimar', 'Guna', 'Gwalior', 'Harda', 'Hoshangabad', 'Indore', 'Jabalpur', 'Jhabua', 'Katni', 'Mandla', 'Mandsaur', 'Morena', 'Narsimhapur', 'Neemuch', 'Panna', 'Raisen', 'Rajgarh', 'Ratlam', 'Rewa', 'Sagar', 'Satna', 'Sehore', 'Seoni', 'Shahdol', 'Shajapur', 'Sheopur', 'Shivpuri', 'Sidhi', 'Singrauli', 'Tikamgarh', 'Ujjain', 'Umaria', 'Vidisha', 'West Nimar'],
    'Maharashtra': ['Ahmadnagar', 'Akola', 'Amravati', 'Aurangabad', 'Bhandara', 'Bid', 'Buldana', 'Chandrapur', 'Dhule', 'Garhchiroli', 'Gondiya', 'Hingoli', 'Jalgaon', 'Jalna', 'Kolhapur', 'Latur', 'Mumbai City', 'Mumbai Suburban', 'Nagpur', 'Nanded', 'Nandurbar', 'Nashik', 'Osmanabad', 'Palghar', 'Parbhani', 'Pune', 'Raigarh', 'Ratnagiri', 'Sangli', 'Satara', 'Sindhudurg', 'Solapur', 'Thane', 'Wardha', 'Washim', 'Yavatmal'],
    'Manipur': ['Bishnupur', 'Chandel', 'Churachandpur', 'Imphal East', 'Imphal West', 'Senapati', 'Tamenglong', 'Thoubal', 'Ukhrul'],
    'Meghalaya': ['East Garo Hills', 'East Khasi Hills', 'Jaintia Hills', 'North Garo Hills', 'Ri Bhoi', 'South Garo Hills', 'South West Garo Hills', 'South West Khasi Hills', 'West Garo Hills', 'West Khasi Hills'],
    'Mizoram': ['Aizawl', 'Champhai', 'Kolasib', 'Lawangtlai', 'Lunglei', 'Mamit', 'Saiha', 'Serchhip'],
    'Nagaland': ['Dimapur', 'Kiphire', 'Kohima', 'Longleng', 'Mokokchung', 'Mon', 'Peren', 'Phek', 'Tuensang', 'Wokha', 'Zunheboto'],
    'NCT of Delhi': ['West'],
    'Odisha': ['Anugul', 'Balangir', 'Baleshwar', 'Bargarh', 'Bauda', 'Bhadrak', 'Cuttack', 'Debagarh', 'Dhenkanal', 'Gajapati', 'Ganjam', 'Jagatsinghapur', 'Jajapur', 'Jharsuguda', 'Kalahandi', 'Kandhamal', 'Kendrapara', 'Kendujhar', 'Khordha', 'Koraput', 'Malkangiri', 'Mayurbhanj', 'Nabarangapur', 'Nayagarh', 'Nuapada', 'Puri', 'Rayagada', 'Sambalpur', 'Subarnapur', 'Sundargarh'],
    'Puducherry': ['Karaikal', 'Mahe', 'Puducherry', 'Yanam'],
    'Punjab': ['Amritsar', 'Barnala', 'Bathinda', 'Faridkot', 'Fatehgarh Sahib', 'Fazilka', 'Firozpur', 'Gurdaspur', 'Hoshiarpur', 'Jalandhar', 'Kapurthala', 'Ludhiana', 'Mansa', 'Moga', 'Muktsar', 'Pathankot', 'Patiala', 'Rupnagar', 'Sahibzada Ajit Singh Nagar', 'Sangrur', 'Shahid Bhagat Singh Nagar', 'Tarn Taran'],
    'Rajasthan': ['Ajmer', 'Alwar', 'Banswara', 'Baran', 'Barmer', 'Bharatpur', 'Bhilwara', 'Bikaner', 'Bundi', 'Chittaurgarh', 'Churu', 'Dausa', 'Dhaulpur', 'Dungarpur', 'Ganganagar', 'Hanumangarh', 'Jaipur', 'Jaisalmer', 'Jalor', 'Jhalawar', 'Jhunjhunun', 'Jodhpur', 'Karauli', 'Kota', 'Nagaur', 'Pali', 'Pratapgarh', 'Rajsamand', 'Sawai Madhopur', 'Sikar', 'Sirohi', 'Tonk', 'Udaipur'],
    'Sikkim': ['East Sikkim', 'North Sikkim', 'South Sikkim', 'West Sikkim'],
    'Tamil Nadu': ['Ariyalur', 'Chennai', 'Coimbatore', 'Cuddalore', 'Dharmapuri', 'Dindigul', 'Erode', 'Kancheepuram', 'Kanniyakumari', 'Karur', 'Krishnagiri', 'Madurai', 'Nagappattinam', 'Namakkal', 'Perambalur', 'Pudukkottai', 'Ramanathapuram', 'Salem', 'Sivaganga', 'Thanjavur', 'The Nilgiris', 'Theni', 'Thiruvallur', 'Thiruvarur', 'Thoothukkudi', 'Tiruchirappalli', 'Tirunelveli', 'Tiruppur', 'Tiruvannamalai', 'Vellore', 'Viluppuram', 'Virudunagar'],
    'Telangana': ['Adilabad', 'Hyderabad', 'Karimnagar', 'Khammam', 'Mahbubnagar', 'Medak', 'Nalgonda', 'Nizamabad', 'Ranga Reddy', 'Warangal'],
    'Tripura': ['Dhalai', 'Gomati', 'Khowai', 'North Tripura', 'Sipahijala', 'South Tripura', 'Unokoti', 'West Tripura'],
    'Uttar Pradesh': ['Agra', 'Aligarh', 'Allahabad', 'Ambedkar Nagar', 'Amethi', 'Amroha', 'Auraiya', 'Azamgarh', 'Baghpat', 'Bahraich', 'Ballia', 'Balrampur', 'Banda', 'Barabanki', 'Bareilly', 'Basti', 'Bijnor', 'Budaun', 'Bulandshahr', 'Chandauli', 'Chitrakoot', 'Deoria', 'Etah', 'Etawah', 'Faizabad', 'Farrukhabad', 'Fatehpur', 'Firozabad', 'Gautam Buddha Nagar', 'Ghaziabad', 'Ghazipur', 'Gonda', 'Gorakhpur', 'Hamirpur', 'Hapur', 'Hardoi', 'Hathras', 'Jalaun', 'Jaunpur', 'Jhansi', 'Kannauj', 'Kanpur Dehat', 'Kanpur Nagar', 'Kasganj', 'Kaushambi', 'Kushinagar', 'Lakhimpur Kheri', 'Lalitpur', 'Lucknow', 'Maharajganj', 'Mahoba', 'Mainpuri', 'Mathura', 'Mau', 'Meerut', 'Mirzapur', 'Moradabad', 'Muzaffarnagar', 'Pilibhit', 'Pratapgarh', 'Rae Bareli', 'Rampur', 'Saharanpur', 'Sambhal', 'Sant Kabir Nagar', 'Sant Ravi Das Nagar', 'Shahjahanpur', 'Shamli', 'Shravasti', 'Siddharth Nagar', 'Sitapur', 'Sonbhadra', 'Sultanpur', 'Unnao', 'Varanasi'],
    'Uttarakhand': ['Almora', 'Bageshwar', 'Chamoli', 'Champawat', 'Dehradun', 'Garhwal', 'Hardwar', 'Nainital', 'Pithoragarh', 'Rudraprayag', 'Tehri Garhwal', 'Udham Singh Nagar', 'Uttarkashi'],
    'West Bengal': ['Alipurduar', 'Bankura', 'Barddhaman', 'Birbhum', 'Dakshin Dinajpur', 'Darjiling', 'Haora', 'Hugli', 'Jalpaiguri', 'Koch Bihar', 'Kolkata', 'Maldah', 'Murshidabad', 'Nadia', 'North 24 Parganas', 'Pashchim Medinipur', 'Purba Medinipur', 'Puruliya', 'South 24 Parganas', 'Uttar Dinajpur'],
}

# Flatten districts
all_districts = []
for state, dists in districts_per_state.items():
    for dist in dists:
        all_districts.append((dist, state))

# Occupations
occupations = ["Engineer", "Teacher", "Doctor", "Farmer", "Clerk", "Businessman", "Student", "Retired", "Unemployed"]

# Age groups
age_groups = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]

# Education levels
education_levels = ["Primary", "Secondary", "Higher Secondary", "Graduate", "Post Graduate", "Illiterate"]

# Industries
industries = ["Agriculture", "Manufacturing", "Services", "IT", "Construction", "Retail"]

# Employment status
employment_statuses = ["Employed", "Unemployed", "Self-Employed", "Student", "Retired"]

# Genders
genders = ["Male", "Female", "Other"]

# Cities (sample)
cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Surat"]

# Output directory
output_dir = r"..\datasets\geodata"
os.makedirs(output_dir, exist_ok=True)

# 1. dataset1.csv - states
with open(os.path.join(output_dir, "dataset1.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["state_name", "population", "population_percent", "male", "female", "rural", "urban", "area_km2", "population_density", "est_unemployment_rate", "est_employed", "area_type"])
    total_pop = 0
    for state in states:
        pop = random.randint(1000000, 200000000)  # synthetic
        total_pop += pop
    for state in states:
        pop = random.randint(1000000, 200000000)
        pop_percent = (pop / total_pop) * 100 if total_pop > 0 else 0
        male = int(pop * 0.51)
        female = pop - male
        rural = int(pop * random.uniform(0.6, 0.8))
        urban = pop - rural
        area = random.uniform(1000, 50000)
        density = pop / area
        unemp = random.uniform(3, 15)
        employed = int(pop * (1 - unemp/100) * 0.5)  # rough
        area_type = random.choice(["Rural", "Urban", "Mixed"])
        writer.writerow([state, pop, round(pop_percent, 2), male, female, rural, urban, round(area, 2), round(density, 2), round(unemp, 2), employed, area_type])

# 2. dataset2.csv - districts
with open(os.path.join(output_dir, "dataset2.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["district_name", "state", "population_district", "literacy_rate_percent"])
    for dist, state in all_districts:
        pop = random.randint(50000, 5000000)
        literacy = random.uniform(60, 95)
        writer.writerow([dist, state, pop, round(literacy, 2)])

# 3. dataset3.csv - expenditures
with open(os.path.join(output_dir, "dataset3.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["state", "district", "income", "age", "occupation", "groceries_exp", "transport_exp", "eating_out_exp", "entertainment_exp", "utilities_exp", "healthcare_exp", "education_exp", "misc_exp", "disposable_income", "potential_savings_groceries", "potential_savings_transport", "potential_savings_eating_out", "potential_savings_entertainment", "potential_savings_utilities", "potential_savings_healthcare", "potential_savings_education", "potential_savings_miscellaneous"])
    for _ in range(10000):  # 10000 rows
        district_name, state_name = random.choice(all_districts)
        income = random.uniform(10000, 200000)
        age = random.randint(18, 80)
        occ = random.choice(occupations)
        exp_groc = random.uniform(1000, 10000)
        exp_trans = random.uniform(500, 5000)
        exp_eat = random.uniform(200, 2000)
        exp_ent = random.uniform(100, 1000)
        exp_util = random.uniform(500, 3000)
        exp_health = random.uniform(200, 5000)
        exp_edu = random.uniform(0, 10000)
        exp_misc = random.uniform(200, 2000)
        total_exp = exp_groc + exp_trans + exp_eat + exp_ent + exp_util + exp_health + exp_edu + exp_misc
        disp_inc = income - total_exp
        pot_sav = [random.uniform(0, e*0.2) for e in [exp_groc, exp_trans, exp_eat, exp_ent, exp_util, exp_health, exp_edu, exp_misc]]
        writer.writerow([state_name, district_name, round(income, 2), age, occ, round(exp_groc, 2), round(exp_trans, 2), round(exp_eat, 2), round(exp_ent, 2), round(exp_util, 2), round(exp_health, 2), round(exp_edu, 2), round(exp_misc, 2), round(disp_inc, 2)] + [round(s, 2) for s in pot_sav])

# 4. dataset5.csv - employment
with open(os.path.join(output_dir, "dataset5.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["state", "district", "employment_status", "age_group", "education_level", "industry", "location", "monthly_salary_inr"])
    for _ in range(10000):
        district_name, state_name = random.choice(all_districts)
        status = random.choice(employment_statuses)
        age_g = random.choice(age_groups)
        edu = random.choice(education_levels)
        ind = random.choice(industries)
        loc = random.choice(["Urban", "Rural"])
        salary = random.uniform(0, 100000) if status == "Employed" else 0
        writer.writerow([state_name, district_name, status, age_g, edu, ind, loc, round(salary, 2)])

# 5. dataset6.csv - customers
with open(os.path.join(output_dir, "dataset6.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["state", "district", "customer_name", "age", "gender", "education_level", "income", "purchase_frequency", "spending"])
    for i in range(10000):
        district_name, state_name = random.choice(all_districts)
        name = f"Customer_{i+1}"
        age = random.randint(18, 80)
        gender = random.choice(genders)
        edu = random.choice(education_levels)
        income = random.uniform(10000, 200000)
        freq = random.uniform(1, 30)  # per month
        spend = random.uniform(1000, 50000)
        writer.writerow([state_name, district_name, name, age, gender, edu, round(income, 2), round(freq, 2), round(spend, 2)])

# 6. city_to_state_mapping.csv
with open(os.path.join(output_dir, "city_to_state_mapping.csv"), "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["city", "state"])
    for city in cities:
        state = random.choice(states)  # random mapping for demo
        writer.writerow([city, state])

print("Datasets generated successfully.")