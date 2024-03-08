import React, { useEffect, useMemo, useState} from 'react';
import {Link, useParams, useNavigate} from 'react-router-dom';
import { AsyncActionType, useGetBook } from '../hooks/bookstore.hook';


const ViewSingleBook: React.FC = () => {
    let { bookId } = useParams<{ bookId: string }>();
    const navigate = useNavigate();
    const [quantityAdjustment, setQuantityAdjustment] = useState(1);
    const { state: bookState, actions } = useGetBook();
    const formatPrice = (price: number) => {
        return `$${price.toFixed(2)}`;
    };

    const totalAmount = useMemo(() => {
        return bookState.payload ? bookState.payload.price * quantityAdjustment : 0;
    }, [bookState.payload]);
    
    const handleCheckout = () => {
        navigate(`/checkout/${bookState.payload?.id}`, { state: { ...bookState.payload, totalAmount } });
    };

    useEffect(() => {
        if(bookId) {
            actions.fetchBook(bookId);
        }
    }, [bookId]);

    useEffect(() => {
        if(bookState.state === AsyncActionType.Success) {
            window.scrollTo(0, 0);
        }
    },[bookState]);

    if (bookState.state === AsyncActionType.Loading) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ height: '100vh' }}>
                <div className="spinner-border" role="status">
                    <span className="sr-only">Loading...</span>
                </div>
                <p className="ml-3">Loading book details...</p>
            </div>
        );
    }

    // Enhanced Error Handling
    if (bookState.state === AsyncActionType.Error) {
        return (
            <div className="container mt-3 alert alert-danger">
                Something went wrong. Please try reloading the page or contact support.
            </div>
        );
    }

    if (!bookState.payload) {
        return <div className="container mt-3 alert alert-warning">Book not found</div>;
    }

    const availabilityIndicator = (bookState.payload?.copiesAvailable ?? 0) > 0 ? 'text-success' : 'text-danger';
    const availabilityText =( bookState.payload?.copiesAvailable ?? 0 )> 0 ? 'Available' : 'Out of Stock';

    const QuantityAdjustmentUI = () => (
        <div>
            <input
                type="number"
                value={quantityAdjustment}
                onChange={(e) => setQuantityAdjustment(Number(e.target.value))}
                className="form-control mb-2"
                min="1"
                max="10"
            />
        </div>
    );

    // Main Render
    return (
        <div className="container mt-5">
            {/* Breadcrumb Navigation */}
            <nav aria-label="breadcrumb">
                <ol className="breadcrumb">
                    <li className="breadcrumb-item"><Link to="/">Home</Link></li>
                    <li className="breadcrumb-item active" aria-current="page">Book Details</li>
                </ol>
            </nav>

            <div className="row">
                {/* Book Image */}
                <div className="col-md-6">
                    <img src={bookState.payload?.image_url} alt={bookState.payload?.title} className="img-fluid rounded"/>
                </div>


                {/* Book Details */}
                <div className="col-md-6">
                    <h2 className="mb-3">{bookState.payload?.title}</h2>
                    <p className="lead"><strong>Price:</strong> {formatPrice(bookState.payload?.price)}</p>
                    <p><strong>Author:</strong> {bookState.payload?.author}</p>
                    <p><strong>Description:</strong> {bookState.payload?.description}</p>
                    <p className={availabilityIndicator}><strong>Copies Available:</strong> {bookState.payload?.copiesAvailable} ({availabilityText})</p>
                    <QuantityAdjustmentUI />
                    <p className="lead"><strong>Price:</strong> {bookState.payload && formatPrice(bookState.payload.price)}</p>
                    <p className="total-price mt-2">Total Price: {formatPrice(totalAmount)}</p>
                    <button onClick={handleCheckout} className="btn btn-outline-success btn-lg">
                        Checkout
                    </button>

                </div>
            </div>
        </div>
    );
};

export default ViewSingleBook;
