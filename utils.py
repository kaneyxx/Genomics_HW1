from Bio import SeqIO
import math
import numpy as np

def extract_and_process_sequence(filename, target_id, start, end):
    """
    Extracts the sequence associated with the given ID from a FASTA file,
    gets the sub-sequence from start to end, converts it to lowercase, 
    and splits by 'n'.
    """
    with open(filename, 'rt') as handle:
        for record in SeqIO.parse(handle, "fasta"):
            if record.id == target_id:
                sub_seq = record.seq[start:end].lower()
                return str(sub_seq).split('n')

    return None  # Return None if target_id not found


def log2_prob_markov_chain(sequence, order, prob_0=None, prob_1=None, prob_2=None):
    assert order in [-1, 0, 1, 2], "Order only accepts -1, 0, 1, and 2."

    # Compute log2 probability of order 0 Markov chain
    log_prob_0 = sum(math.log2(prob_0[char]) for char in sequence)
    if order==0:
        return log_prob_0   
    
    # Compute log2 probability of order 1 Markov chain
    # Compute the probability of first character 
    log_prob_1 = math.log2(prob_0[sequence[0]])
    # Then compute transition probability of first to second character
    for i in range(1, len(sequence)):
        log_prob_1 += math.log2(prob_1[sequence[i-1]][sequence[i]])
    if order==1:
        return log_prob_1  
    
    # Compute log2 probability of order 2 Markov chain
    # Compute the probability of first 2 characters
    log_prob_2 = math.log2(prob_1[sequence[0]][sequence[1]]) + math.log2(prob_0[sequence[0]])
    # Then compute transition probability of second to third character
    for i in range(2, len(sequence)):
        log_prob_2 += math.log2(prob_2[sequence[i-2]+sequence[i-1]][sequence[i]])
    if order==2:
        return log_prob_2
    
    # Return probabilities of all orders
    else:
        return log_prob_0, log_prob_1, log_prob_2


def viterbi_algorithm_log(hmm, sequence):
    num_states = len(hmm.states)
    num_symbols = len(sequence)
    
    # Initialization
    viterbi_log = np.full((num_states, num_symbols), -np.inf)
    backpointer = np.zeros((num_states, num_symbols), dtype=int)
    
    # Convert sequence symbols to indices
    sequence_idx = [hmm.symbols.index(symbol.upper()) for symbol in sequence]
    
    # Initialize first column of viterbi matrix
    for state in range(num_states):
        viterbi_log[state, 0] = np.log(hmm.initial_probs[state]) + np.log(hmm.emission_probs[state, sequence_idx[0]])
    
    # Forward pass
    for t in range(1, num_symbols):
        for state in range(num_states):
            trans_log_probs = [viterbi_log[prev_state, t-1] + np.log(hmm.transition_probs[prev_state, state]) for prev_state in range(num_states)]
            max_trans_log_prob = max(trans_log_probs)
            backpointer[state, t] = np.argmax(trans_log_probs)
            viterbi_log[state, t] = max_trans_log_prob + np.log(hmm.emission_probs[state, sequence_idx[t]])
    
    # Backtracking
    best_path_pointer = np.argmax(viterbi_log[:, -1])
    best_log_prob = np.max(viterbi_log[:, -1])
    best_path = [best_path_pointer]
    for t in range(num_symbols-1, 0, -1):
        best_path_pointer = backpointer[best_path_pointer, t]
        best_path.insert(0, best_path_pointer)
    
    best_path_states = [hmm.states[state] for state in best_path]
    
    return best_path_states, best_log_prob


# Forward Algorithm with scaling
def forward_algorithm_scaled(hmm, sequence):
    num_states = len(hmm.states)
    num_symbols = len(sequence)
    
    # Create matrices to store the forward probabilities and scaling factors
    alpha = np.zeros((num_symbols, num_states))
    scaling_factors = np.zeros(num_symbols)
    
    # Initialization
    for i, state in enumerate(hmm.states):
        symbol_idx = hmm.symbols.index(sequence[0].upper())
        # For simplicity, assume equal initial probabilities for each state: 1/num_states
        alpha[0, i] = (1/num_states) * hmm.emission_probs[i, symbol_idx]
    
    # Scale alpha values for t=0
    scaling_factors[0] = 1.0 / np.sum(alpha[0, :])
    alpha[0, :] *= scaling_factors[0]
    
    # Recursion
    for t in range(1, num_symbols):
        for i, state in enumerate(hmm.states):
            symbol_idx = hmm.symbols.index(sequence[t].upper())
            emission_prob = hmm.emission_probs[i, symbol_idx]
            
            transition_probs = hmm.transition_probs[:, i]
            alpha[t, i] = emission_prob * np.sum(alpha[t-1, :] * transition_probs)
        
        # Scale alpha values for time t
        scaling_factors[t] = 1.0 / np.sum(alpha[t, :])
        alpha[t, :] *= scaling_factors[t]
    
    # Compute the log probability using the scaling factors
    log_prob_sequence = -np.sum(np.log2(scaling_factors))
    
    return alpha, scaling_factors, log_prob_sequence


# Backward Algorithm with scaling
def backward_algorithm_scaled(hmm, sequence):
    num_states = len(hmm.states)
    num_symbols = len(sequence)
    
    # Initialization
    beta = np.zeros((num_symbols, num_states))
    scaling_factors = np.zeros(num_symbols)
    
    # Set beta for time T to 1, scaled by a factor
    beta[num_symbols-1, :] = 1
    scaling_factor = 1 / np.sum(beta[num_symbols-1, :])
    beta[num_symbols-1, :] *= scaling_factor
    scaling_factors[num_symbols-1] = scaling_factor
    
    # Backward steps
    for t in range(num_symbols-2, -1, -1):
        for i in range(num_states):
            beta[t, i] = 0
            for j in range(num_states):
                symbol_idx = hmm.symbols.index(sequence[t+1].upper())
                transition_prob = hmm.transition_probs[i, j]
                emission_prob = hmm.emission_probs[j, symbol_idx]
                beta[t, i] += beta[t+1, j] * transition_prob * emission_prob
        
        # Scale beta values for time t
        scaling_factor = 1 / np.sum(beta[t, :])
        beta[t, :] *= scaling_factor
        scaling_factors[t] = scaling_factor
    
    # Calculate log probability
    log_prob = 0
    for i in range(num_states):
        transition_probs = hmm.transition_probs[i]
        emission_prob = hmm.emission_probs[i, hmm.symbols.index(sequence[0].upper())]
        log_prob += beta[0, i] * transition_probs * emission_prob
    
    log_prob = np.log2(log_prob)
    
    return beta, scaling_factors, log_prob

def compute_xi_gamma(hmm, sequence, alpha, beta):
    num_states = len(hmm.states)
    num_symbols = len(sequence)
    
    xi = np.zeros((num_symbols - 1, num_states, num_states))
    gamma = np.zeros((num_symbols, num_states))
    
    for t in range(num_symbols - 1):
        xi_sum = 0
        for i, state in enumerate(hmm.states):
            for j, next_state in enumerate(hmm.states):
                symbol_idx = hmm.symbols.index(sequence[t+1].upper())
                transition_prob = hmm.transition_probs[i, j]
                emission_prob = hmm.emission_probs[j, symbol_idx]
                
                xi[t, i, j] = alpha[t, i] * transition_prob * emission_prob * beta[t+1, j]
                xi_sum += xi[t, i, j]
        
        # Normalize xi values to avoid underflow
        xi[t, :, :] /= xi_sum
        
        # Compute gamma values using xi
        gamma[t, :] = np.sum(xi[t, :, :], axis=1)
    
    # For gamma at the last position, it's just the scaled alpha values
    gamma[num_symbols-1, :] = alpha[num_symbols-1, :]
    
    return xi, gamma


def m_step(hmm, sequence, xi, gamma):
    num_states = len(hmm.states)
    num_symbols = len(sequence)
    
    # Update transition probabilities
    for i in range(num_states):
        for j in range(num_states):
            hmm.transition_probs[i, j] = np.sum(xi[:, i, j]) / np.sum(gamma[:-1, i])
    
    # Update emission probabilities
    for i in range(num_states):
        for k, symbol in enumerate(hmm.symbols):
            indices = [t for t, x in enumerate(sequence) if x.upper() == symbol]
            hmm.emission_probs[i, k] = np.sum(gamma[indices, i]) / np.sum(gamma[:, i])
    
    return hmm