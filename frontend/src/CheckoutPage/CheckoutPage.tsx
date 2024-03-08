import React, { useEffect, useState } from 'react';
import { useLocation, useParams, useNavigate } from 'react-router-dom';
import { AsyncActionType, useCheckout } from '../hooks/bookstore.hook';

const countries = ["Estonia", "Finland"];

type CheckoutForm = {
    userName: string;
    userContact: string;
    creditCardNumber: string;
    creditCardExpirationDate: string;
    creditCardCVV: string;
    userComment: string;
    discountCode: string;
    shippingMethod: string;
    giftMessage: string;
    billingAddressStreet: string;
    billingAddressCity: string;
    billingAddressState: string;
    billingAddressZip: string;
    billingAddressCountry: string;
    giftWrapping: boolean;
    termsAndConditionsAccepted: boolean;
};

const CheckoutPage: React.FC = () => {
    const { bookId } = useParams<{ bookId: string }>();
    const navigate = useNavigate();
    const location = useLocation();
    const book = location.state;

    const [formData, setFormData] = useState<CheckoutForm>({
        userName: '',
        userContact: '',
        creditCardNumber: '',
        creditCardExpirationDate: '',
        creditCardCVV: '',
        userComment: '',
        discountCode: '',
        shippingMethod: '',
        giftMessage: '',
        billingAddressStreet: '',
        billingAddressCity: '',
        billingAddressState: '',
        billingAddressZip: '',
        billingAddressCountry: 'Select a country',
        giftWrapping: false,
        termsAndConditionsAccepted: false
    });

    const { state: checkoutState, actions } = useCheckout()

    useEffect(() => {
        if (checkoutState.state === AsyncActionType.Success && checkoutState.payload) {
            navigate('confirmation', { state: { orderStatusResponse: checkoutState.payload } });
            return;
        }
        if (checkoutState.state === AsyncActionType.Error) {
            alert('An error occurred while processing your order. Please try again later.');
        }
    }, [checkoutState, navigate]);

    const handleInputChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value, type, checked } = event.target as HTMLInputElement;
        setFormData({
            ...formData,
            [name]: type === 'checkbox' ? checked : value,
        });
    };

    const handleCheckout = async (event: React.FormEvent) => {
        event.preventDefault();
        actions.checkout({
            user: {
                name: formData.userName,
                contact: formData.userContact,
            },
            creditCard: {
                number: formData.creditCardNumber,
                expirationDate: formData.creditCardExpirationDate,
                cvv: formData.creditCardCVV,
            },
            userComment: formData.userComment,
            items: [
                {
                    name: book.title,
                    quantity: 1,
                },
            ],
            discountCode: formData.discountCode,
            shippingMethod: formData.shippingMethod,
            giftMessage: formData.giftMessage,
            billingAddress: {
                street: formData.billingAddressStreet,
                city: formData.billingAddressCity,
                state: formData.billingAddressState,
                zip: formData.billingAddressZip,
                country: formData.billingAddressCountry,
            },
            termsAndConditionsAccepted: formData.termsAndConditionsAccepted,
            notificationPreferences: ['email'],
            device: {
                type: 'Smartphone',
                model: 'Samsung Galaxy S10',
                os: 'Android 10.0.0',
            },
            browser: {
                name: 'Chrome',
                version: '85.0.4183.127',
            },
            appVersion: '3.0.0',
            screenResolution: '1440x3040',
            referrer: 'https://www.google.com',
            deviceLanguage: 'en-US',
        });

    };


    return (
        <div className="container mt-5">
            <h1 className="text-center mb-4">Checkout</h1>
            <form onSubmit={handleCheckout} className="card p-4 shadow">
                <h2 className="mb-3">Book Details</h2>
                <p>Proceeding with the checkout for book ID: {bookId}</p>

                {/* User Information */}
                <div className="row">
                    <div className="col-md-6">
                        <h3>User Information</h3>
                        <div className="mb-3">
                            <label htmlFor="name" className="form-label">Name</label>
                            <input type="text" className="form-control" id="name" name="userName" value={formData.userName}
                                onChange={handleInputChange} required />
                        </div>
                        <div className="mb-3">
                            <label htmlFor="contact" className="form-label">Contact</label>
                            <input type="tel" className="form-control" id="contact" name="userContact"
                                value={formData.userContact} onChange={handleInputChange} required />
                        </div>

                    </div>
                    <div className="col-md-6">
                        <h3>Billing Address</h3>
                        {/* Address */}
                        {/* Street */}
                        <div className="mb-3">
                            <label htmlFor="street" className="form-label">Street</label>
                            <input type="text" className="form-control" id="street" name="billingAddressStreet"
                                value={formData.billingAddressStreet} onChange={handleInputChange} required />
                        </div>
                        {/* City */}
                        <div className="mb-3">
                            <label htmlFor="city" className="form-label">City</label>
                            <input type="text" className="form-control" id="city" name="billingAddressCity"
                                value={formData.billingAddressCity} onChange={handleInputChange} required />
                        </div>
                        {/* State */}
                        <div className="mb-3">
                            <label htmlFor="state" className="form-label">State</label>
                            <input type="text" className="form-control" id="state" name="billingAddressState"
                                value={formData.billingAddressState} onChange={handleInputChange} required />
                        </div>
                        {/* Zip */}
                        <div className="mb-3">
                            <label htmlFor="zip" className="form-label">Zip</label>
                            <input type="text" className="form-control" id="zip" name="billingAddressZip"
                                value={formData.billingAddressZip} onChange={handleInputChange} required />
                        </div>
                        {/* Country */}
                        <div className="mb-3">
                            <label htmlFor="country" className="form-label">Country</label>
                            <select className="form-control" id="country" name="billingAddressCountry"
                                value={formData.billingAddressCountry} onChange={handleInputChange} required>
                                <option value="">Select a country</option>
                                {countries.map((country, index) => (
                                    <option key={index} value={country}>{country}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                {/* Payment Details */}
                <div className="row mt-4">
                    <div className="col-md-6">
                        <h3>Payment Details</h3>
                        <div className="mb-3">
                            <label htmlFor="creditCardNumber" className="form-label">Credit Card Number</label>
                            <input type="text" className="form-control" id="creditCardNumbe" name="creditCardNumber"
                                value={formData.creditCardNumber} onChange={handleInputChange} required />
                        </div>
                        <div className="mb-3">
                            <label htmlFor="creditCardExpirationDate" className="form-label">Expiration Date</label>
                            <input
                                type="text"
                                className="form-control"
                                id="creditCardExpirationDate"
                                name="creditCardExpirationDate"
                                value={formData.creditCardExpirationDate}
                                onChange={handleInputChange}
                                placeholder="MM/YY"
                                required
                                pattern="\d{2}/\d{2}" // Simple pattern for MM/YY format
                                title="Enter date in MM/YY format"
                            />
                        </div>

                        <div className="mb-3">
                            <label htmlFor="creditCardCVV" className="form-label">CVV</label>
                            <input
                                type="text"
                                className="form-control"
                                id="creditCardCVV"
                                name="creditCardCVV"
                                value={formData.creditCardCVV}
                                onChange={handleInputChange}
                                required
                                maxLength={4}
                                pattern="\d{3,4}"
                                title="CVV should be a 3 or 4 digit number"
                            />
                        </div>

                    </div>
                    <div className="col-md-6">
                        <h3>Additional Information</h3>
                        <div className="mb-3">
                            <label htmlFor="userComment" className="form-label">User Comment</label>
                            <textarea className="form-control" id="userComment" name="userComment"
                                value={formData.userComment} onChange={handleInputChange} />
                        </div>
                        {/* Discount Code */}
                        <div className="mb-3">
                            <label htmlFor="discountCode" className="form-label">Discount Code</label>
                            <input type="text" className="form-control" id="discountCode" name="discountCode"
                                value={formData.discountCode} onChange={handleInputChange} />
                        </div>
                        {/* Shipping Method */}
                        <div className="mb-3">
                            <label htmlFor="shippingMethod" className="form-label">Shipping Method</label>
                            <input type="text" className="form-control" id="shippingMethod" name="shippingMethod"
                                value={formData.shippingMethod} onChange={handleInputChange} />
                        </div>
                    </div>
                </div>

                <div className="form-group mt-4">
                    <div className="form-check">
                        <input type="checkbox" className="form-check-input" id="termsAndConditions"
                            name="termsAndConditionsAccepted" checked={formData.termsAndConditionsAccepted}
                            onChange={handleInputChange} required />
                        <label className="form-check-label" htmlFor="termsAndConditions">I accept the terms and
                            conditions</label>
                    </div>
                </div>

                <button type="submit" className="btn btn-outline-success btn-lg mt-3">Submit</button>
            </form>
        </div>
    );
};

export default CheckoutPage;
