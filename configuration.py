slices = {}
n_slices = 0
n_users = int(input('Enter number of users: '))
global_ip = 112
global_subnet = 45
users_slices = {}
users_n_slices = {}  

answers = [n_users]  # Store the answers, starting with the number of users

for user_id in range(1, n_users + 1):
    user_slices = {}
    user_n_slices = int(input(f'Enter number of slices for user {user_id}: '))
    answers.append(user_n_slices)  # Add the number of slices for this user
    users_n_slices[user_id] = user_n_slices
    user_total_slices = 0

    for i in range(user_n_slices):
        dnn = input(f'Enter DNN for slice {i + 1} of user {user_id}: ')
        bw = input(f'Enter bandwidth (Mbps) for slice {i + 1} of user {user_id}: ')
        
        # Append the answers to the list
        answers.extend([dnn, bw])
        
        user_slices[i] = {
            'dnn': dnn,
            'bw': bw,
            'ip': '192.168.0.' + str(global_ip),
            'subnet': '10.' + str(global_subnet) + '.0.1'
        }
        
        slices[n_slices] = user_slices[i]
        n_slices += 1
        user_total_slices += 1
        global_ip += 1
        global_subnet += 1

    users_slices[user_id] = user_slices
    users_n_slices[user_id] = user_total_slices

# Writing only the answers to a file
with open('user_slices_answers.txt', 'w') as file:
    for answer in answers:
        file.write(f"{answer}\n")

