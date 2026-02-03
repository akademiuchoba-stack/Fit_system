
import numpy as np

def bayesian_update(prior_mu: float, prior_sigma: float, feedback_value: float, likelihood_sigma: float = 1.5):
    """
    Обновление параметров размера на основе Байесовского вывода (Normal-Normal Conjugate).
    
    :param prior_mu: Текущее среднее значение замера в БД.
    :param prior_sigma: Текущая неопределенность замера.
    :param feedback_value: Реальный замер, полученный от пользователя.
    :param likelihood_sigma: Доверие к замеру пользователя (шум измерения).
    """
    
    # Формулы обновления для сопряженного априорного распределения
    # Новое среднее (mu_post) - это взвешенное среднее между априорным и новым данными
    precision_prior = 1.0 / (prior_sigma ** 2)
    precision_likelihood = 1.0 / (likelihood_sigma ** 2)
    
    mu_post = (prior_mu * precision_prior + feedback_value * precision_likelihood) / (precision_prior + precision_likelihood)
    
    # Новая сигма (sigma_post) всегда меньше предыдущей (увеличиваем уверенность)
    sigma_post = np.sqrt(1.0 / (precision_prior + precision_likelihood))
    
    return float(mu_post), float(sigma_post)
